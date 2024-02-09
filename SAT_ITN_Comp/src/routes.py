"""
	Module for processing a routes shapefile so it can be used to find the corresponding links.
"""

##### IMPORTS #####
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, MultiPoint, LineString, MultiLineString
from shapely import ops
from argparse import ArgumentParser
import sys, os

# Script modules
from utils import filePath, outputCsv, overlapLength, getCoords, getSingleLine, \
                    calculateAngle, calcLengthDiff, outpath, TimeTaken

##### CLASS #####
class RouteProcessing:
    """
        Class for processing routes shapefile so it can be used to find the corresponding links.
    """
    # Set dafault variables
    ID_COLUMN = 'ROUTE_ID'
    SEGMENT_ID = 'SEGMENT_ID'
    SEGMENT = 1000
    PATH = None

    def __init__(self, shp, idCol=None, group=False):
        """ Initilising the class which will preprocess routes shapefiles. """
        # Set ID column if given
        if not idCol is None:
            self.ID_COLUMN = idCol

        # Accept GeoDataFrame
        if isinstance(shp, gpd.GeoDataFrame):
            self.routes = shp
        else:
            # Check path
            filePath(shp, argErr=False)
            # Read shapefile
            self.routes = gpd.read_file(shp)
            self.PATH = shp
        # Check if ID column is present
        if not self.ID_COLUMN in self.routes:
            raise ValueError(f"Missing column with route IDs expected '{self.ID_COLUMN}'")

        # Set crs variables
        self.CRS = self.routes.crs

        # Check if the features are lines or multi lines
        geoType = self.routes.geom_type
        correctType = (geoType == 'LineString') | (geoType == 'MultiLineString')
        if not correctType.all():
            wrong = (correctType==False).sum()
            tot = len(correctType)
            perc = wrong / tot
            raise ValueError(f'{wrong:,} out of {tot:,} ({perc:.0%}) features are not lines')

        return

    def setSegment(self, segment=None):
        if not segment is None:
            self.SEGMENT = float(segment)
        return self.SEGMENT

    def process(self, segment=None):
        """ Loop through the features converting them to a single line a and splitting it into segments. """
        # Set segment if given
        self.setSegment(segment=segment)
        # Get line segments
        segs = self.routes.apply(self.segment, axis=1)
        segs = pd.concat([self.routes[self.ID_COLUMN], segs], axis=1)

        # Melt the DataFrame to reshape in so segments have separate rows
        segs = segs.melt(id_vars=[self.ID_COLUMN], var_name='Segment',
                                        value_name='SegGeom').sort_values(self.ID_COLUMN)
        # Drop rows with nan in SegGeom
        segs = segs.dropna(subset=['SegGeom'])
        segs = segs.reset_index().drop('index', axis=1)

        # Create segment ID column
        segs[self.SEGMENT_ID] = segs[self.ID_COLUMN].astype(str) + '_' + segs['Segment'].astype(str)
        segs = segs.set_geometry('SegGeom')
        segs.crs = self.CRS
        # Remove the Z coordinate from any LineStrings that have it
        segs.geometry = segs.geometry.apply(self.removeZ)

        self.segmented = segs

        return segs

    def segment(self, lineString, segment=None):
        """ Segment a LineString (or MultiLineString) to make many segments each with a minimum <<segments>> distance. """
        # Set segment if given
        self.setSegment(segment=segment)
        # Get geometry column if series given
        if isinstance(lineString, pd.Series):
            lineString = lineString.geometry
        # Convert to list for looping if single line string given
        if isinstance(lineString, LineString):
            lineString = [lineString]

        # Loop through multi lines appending them all to a single list
        splitLines = []
        for line in lineString:
            # Get the start point of the line
            splitPoints = [Point(line.coords[0])]

            # Loop through points
            for p in line.coords[1:]:
                # Create point
                p = Point(p)
                # Check distance
                if splitPoints[-1].distance(p) >= self.SEGMENT:
                    splitPoints.append(p)
            # Create multi point shape
            splitPoints = MultiPoint(splitPoints)

            # Split line based on points
            splitLines += list(ops.split(line, splitPoints))

        # Return lines in a series
        names = [f'SEG{i+1}' for i in range(len(splitLines))]
        return pd.Series(splitLines, index=names)

    def writeShp(self, overwrite=True, outPath=None):
        """ Write the segmented shapefile. """
        # Create new path
        if outPath is None:
            loc = self.PATH.rfind('.')
            outPath = self.PATH[:loc] + '_Segmented.shp'
        elif not overwrite:
            loc = outPath.rfind('.')

        # Check for overwriting and add number if required
        if not overwrite:
            count = 1
            origPath = str(outPath)
            while not overwrite and os.path.exists(outPath):
                outPath = origPath[:loc] + f'_{count}.shp'
                count += 1

        # Output file
        self.segmented.to_file(outPath)
        return outPath

    @staticmethod
    def removeZ(line3D, check=True):
        """ Removes the Z coordinate from LineString or MultiLineString object. """
        # Get the geometry
        if isinstance(line3D, pd.Series):
            line3D = line3D.geometry
        # Check the type try to convert MultiLineString to LineStrings
        if isinstance(line3D, MultiLineString):
            line3D = ops.linemerge(line3D)
        # If it is a single LineString then create a list containing it so the for loop can be used
        if isinstance(line3D, LineString):
            line3D = [line3D]
        elif not isinstance(line3D, MultiLineString):
            raise TypeError(f'Incorrect type given expected LineString got {type(line3D)}')

        # Loop through all lines in MultiLineString or just the single line
        lines = []
        for i in line3D:
            # Convert coords to array and get the first 2 values (x, y) of each coordinate set
            line2D = LineString(np.array(i.coords).T[:2].T)
            # Check if the 2D line equals the 3D line
            if check and not line2D.equals(i):
                raise ValueError('After removing the Z coordinate of the line it is no longer equal i.e. the Z value must not have been 0')
            # Append to list
            lines.append(line2D)

        # Convert to MultiLineString if needed
        if len(lines) > 1:
            line2D = MultiLineString(lines)

        return line2D

    def groupSegments(self, lookupPath, segmentedPath, linksPath=None, linkIdCol=None, buffer=None):
        """ Group the segmented routes back into routes. """
        # Read lookup CSV
        lookupCsv = pd.read_csv(lookupPath)
        cols = lookupCsv.columns

        # Read segmented shapefile
        segmentedShp = gpd.read_file(segmentedPath)
        # Check if required columns are present
        for i in (self.SEGMENT_ID, self.ID_COLUMN):
            if not i in segmentedShp:
                raise ValueError(f"Missing column '{i}'")

        # Create lookup lists
        to_replace = segmentedShp[self.SEGMENT_ID].tolist()
        replacement = segmentedShp[self.ID_COLUMN].tolist()
        # Replace values in ID column
        lookupCsv['SATURN_Link_ID'] = lookupCsv['SATURN_Link_ID'].replace(to_replace, replacement)

        # Drop duplicates
        lookupCsv = lookupCsv.drop_duplicates(['SATURN_Link_ID', 'ITN_Link_ID'])
        # Recalculate lengths
        lengths = self.routes.loc[:, [self.ID_COLUMN, 'geometry']]
        lengths['length'] = lengths.geometry.length
        lookupCsv = lookupCsv.merge(lengths, left_on='SATURN_Link_ID', right_on=self.ID_COLUMN,
                                    validate='many_to_one')
        lookupCsv['SATURN_Length(m)'] = lookupCsv['length']
        # Convert back to DataFrame
        lookupCsv = pd.DataFrame(lookupCsv.loc[:, cols])

        # Recalculate overlap length
        if linksPath is None:
            # Set overlap length and angle columns to nan
            lookupCsv.loc[:, ['ITN_Overlap_Length(m)', 'ITN_SAT_Angle']] = np.nan
        else:
            linksShp = gpd.read_file(linksPath)
            lookupCsv = self.recalcOverlap(lookupCsv, linksShp, linkIdCol, buffer)

        return lookupCsv

    @staticmethod
    def getEndpoints(line):
        """
            Get the start and end coordinates for each line in GeoDataFrame.
        """
        if isinstance(line, MultiLineString):
            start = getCoords(line[0], 0, pointType=False)
            end = getCoords(line[-1], -1, pointType=False)
        else:
            start = getCoords(line, 0, pointType=False)
            end = getCoords(line, -1, pointType=False)

        return np.array([start, end])

    def recalcOverlap(self, lookup, linksShp, linkIdCol, buffer):
        """
            Recalculate overlap length and the angle between the links.

            Parameters:
                lookup: pandas.DataFrame
                    DataFrame containing the lookup data, must contain the lookup ID columns.
                linksShp: geopandas.GeoDataFrame
                    Shapefile containing links data, must have
                    lookup ID corresponding to ID in lookup.
                linkIdCol: str
                    Name of the column containing link IDs.
                buffer: int
                    Radius for the buffer around the routes to used when calculating overlap.
            Returns:
                lookup: pandas.DataFrame
                    Same DataFrame given but with the overlap length and angle column updated.
        """
        # Loop through the routes ID column
        for routeId in lookup['SATURN_Link_ID'].unique():
            # Get the route geometry from the shapefile
            try:
                routeGeom = self.routes.loc[self.routes[self.ID_COLUMN]==routeId, 'geometry']
                singLine = getSingleLine(routeGeom.geometry.iloc[0])
                routeGeom = pd.Series({'geometry':singLine})
            except IndexError as e:
                print(f'Could not find {routeId} in routes shapefile.')
                continue

            # Loop through all the links found
            routeCond = lookup['SATURN_Link_ID'] == routeId
            for lookId in lookup.loc[routeCond, 'ITN_Link_ID']:
                # Get the link geometry from shapefile
                try:
                    linkGeom = linksShp.loc[linksShp.loc[:, linkIdCol]==lookId, 'geometry']
                    singLine = getSingleLine(linkGeom.geometry.iloc[0])
                    linkGeom = pd.Series({'geometry':singLine})
                except IndexError as e:
                    print(f'Could not find {lookId} in links shapefile.')
                    continue

                # Get location for updating lookup
                cond = routeCond & (lookup['ITN_Link_ID'] == lookId)
                # Check cond doesn't return more than one
                if cond.sum() > 1:
                    raise ValueError(f'Too many rows found for route: {routeId}, link: {lookId}')

                # Calculate overlap length
                lookup.loc[cond, 'ITN_Overlap_Length(m)'] = overlapLength(routeGeom, linkGeom, buffer)
                # Calculate angle
                rLine = self.getEndpoints(routeGeom.geometry)
                lLine = self.getEndpoints(linkGeom.geometry)
                try:
                    angle = calculateAngle(rLine, lLine)
                except ValueError as e:
                    print(f'ValueError: Route: {routeId}, Link: {lookId} - {e}')
                    angle = np.nan
                lookup.loc[cond, 'ITN_SAT_Angle'] = angle

        return lookup


##### MAIN #####
if __name__ == '__main__':
    # Setup parser
    parser = ArgumentParser(description='Script for preprocessing a routes shapefile before running the ITN correspondance.')
    parser.add_argument('shapefile', type=filePath,
                        help='Path to routes shapefile')
    parser.add_argument('--segmented_path', type=str, default=None,
                        help="Path for the segmented shapefile. Required if using '--group'")
    parser.add_argument('-i', '--id_column', type=str, default=None,
                        help='Name of the column in the shapefile containing unique route IDs.')
    parser.add_argument('-s', '--segment', type=int, default=None,
                        help='Rough minimum value for each segment (simple implementation so length can vary). Length will be in CRS units.')
    parser.add_argument('--overwrite', default=True, action='store_false',
                        help='Set overwrite to false.')
    parser.add_argument('-g', '--group', default=False, action='store_true',
                        help='Will regroup the segmented csv lookup file.')
    parser.add_argument('--lookup_csv', default=None, type=filePath,
                        help="Segmented CSV lookup file to be regrouped, required if using '--group'.")
    parser.add_argument('--link_shp', type=str, default=None,
                        help='Path to link shapefile to be used for recalculating overlap length.')
    parser.add_argument('--overlap_buffer', type=int, default=100,
                        help='Radius of buffer around routes, used for calculating overlap length.')
    parser.add_argument('--link_id_col', type=str, default='link_id',
                        help='Name of the column containing the link IDs.')
    # Get arguments
    args = parser.parse_args()
    # Check if required group arguments are present
    if args.group:
        for i in ('lookup_csv', 'segmented_path'):
            if getattr(args, i) is None:
                parser.error(f'--group requires --{i}')

    # Start timer
    timer = TimeTaken()
    done = lambda: print('\tDone in', timer.getLapTime(newLap=True))

    # Initiate class
    print('Reading shapefile')
    routeProcess = RouteProcessing(args.shapefile, idCol=args.id_column, group=args.group)
    done()

    if not args.group:
        # Produce segments
        print('Creating segments')
        segmented = routeProcess.process(segment=args.segment)
        done()

        # Output new shapefile
        print('Writing new shapefile')
        outPath = routeProcess.writeShp(overwrite=args.overwrite)
        print(f'\tWritten to: {outPath}')
        done()

    else:
        # Group segments
        print('Grouping segments')
        lookupCsv = routeProcess.groupSegments(args.lookup_csv, args.segmented_path,
                                            linksPath=args.link_shp, linkIdCol=args.link_id_col,
                                            buffer=args.overlap_buffer)
        done()

        # Output new lookup csv
        print('Writing grouped lookup csv')
        out = outpath(args.lookup_csv, 'Regrouped', filetype='csv')
        print(f'\t{out}')
        outputCsv(lookupCsv, out)
        done()

        # Calculate length difference
        print('Calculating length difference')
        groupCol = 'SATURN_Link_ID'
        lengthCols = {'SATURN_Length(m)':'first', 'ITN_Overlap_Length(m)':'sum'}
        lengthDiff = calcLengthDiff(lookupCsv, groupCol, lengthCols)
        done()
        # Write length difference to csv
        print('Writing length difference csv')
        out = outpath(out, 'LengthDiff', filetype='csv')
        print(f'\t{out}')
        outputCsv(lengthDiff, out)
        done()


    print('Finished, total time', timer.getTimeTaken())
