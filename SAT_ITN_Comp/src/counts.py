"""
	Module to find the closest link, in the correct direction, for count sites (shapefile of points).
"""

##### IMPORTS #####
import geopandas as gpd
from argparse import ArgumentParser
import numpy as np
import pandas as pd

# Script modules
from utils import calculateAngle, getCoords, outputCsv, outpath, closestLine, filePath

##### CLASS #####
class CountLookup:
    """
        Class to perform a lookup between count points and model links.
    """
    # EXPECTED COLUMNS
    COUNTS_COLS = {'COUNT_ID':'unique_id', 'DIRECTION':'Direction'}
    LINKS_COLS = {'LINK_ID':'Link_ID'}
    # Expected directions
    DIRECTIONS = {'NB':None, 'EB':None, 'SB':None, 'WB':None}
    # BUFFERS
    COUNT_BUFFER = 100

    def __init__(self, counts, links):
        """
            Class for performing lookup between count points and model links,
            init will read both shapefiles and do a check on expected columns.

            Parameters:
                counts: str
                    Path to the counts shapefile.
                links: str
                    Path to the links shapefile
            Returns:
                None
        """
        # Read shapefiles
        countShp = gpd.read_file(counts)
        linkShp = gpd.read_file(links)
        # Get only columns required, will return error if columns are missing
        self.countShp = countShp[[*self.COUNTS_COLS.values(), 'geometry']]
        self.linkShp = linkShp[[*self.LINKS_COLS.values(), 'geometry']]
        # Rename columns
        self.countShp = self.countShp.rename(columns={v:k for k, v in self.COUNTS_COLS.items()})
        self.linkShp = self.linkShp.rename(columns={v:k for k, v in self.LINKS_COLS.items()})

        return

    def calcDir(self):
        """
            Calculate the direction of the links shapefile, as an angle from the y axis.
        """
        def bearing(x):
            """ Calculate angle from y axis, using calculateAngle function, and catch errors. """
            try:
                return calculateAngle(yLine, x, directed=True)
            except ValueError as e:
                print(f'ERROR: {e}')
                return np.nan

        # Line up the y axis to measure angles from
        yLine = [(0,0), (0,1)]
        # Get start and end points of line
        lineEnds = []
        for i in (0, -1):
            # Get array of coordinates
            coords = self.linkShp.geometry.apply(getCoords, args=(i,), pointType=False).values
            lineEnds.append(coords)
        # Combine start and end into a list
        self.linkShp['LineEnds'] = np.array(lineEnds).T.tolist()
        self.linkShp['Angle'] = self.linkShp.LineEnds.apply(bearing)
        # Drop LineEnds
        self.linkShp = self.linkShp.drop(columns='LineEnds')
        return

    def lookupCount(self, countRow):
        """
            Find the link for a single count.

            Parameters:
                countRow: geopandas.GeoSeries
                    The row of data for a single count.
            Returns:
                linkData: dict
                    The link data for the corresponding link.
        """
        # Bearing dict
        bearings = {'NB':(0, 360), 'EB':(90,), 'SB':(180,), 'WB':(270,)}
        # Setup output dictionary
        outDict = {'Count_ID':countRow['COUNT_ID'], 'Count_Direction':countRow['DIRECTION']}
        # Filter links
        links = self.linkShp[self.linkShp.intersects(countRow.geometry.buffer(self.COUNT_BUFFER))]
        # Find closest line(s)
        closest, numFound = closestLine(countRow.geometry, links)
        if numFound == 1:
            # Add found data to dict
            outDict['Link_ID'] = closest['LINK_ID'].iloc[0]
            outDict['Link_Angle'] = closest['Angle'].iloc[0]
        elif numFound > 1:
            # Find the link with the angle closest to the direction given
            try:
                bears = bearings[countRow['DIRECTION']]
            except KeyError as e:
                outDict['Comment'] = f"ERROR: Cannot find '{e}'"
                return outDict
            # Find the angle difference for all links
            angleDiff = []
            # Will only loop for NB
            for ang in bears:
                diff = abs(closest['Angle'] - ang)
                angleDiff.append(diff)
            # Create dataframe
            angleDiff = pd.concat(angleDiff)
            # Find minimum angle difference
            ind = angleDiff[angleDiff == angleDiff.min()].index
            closest = closest.loc[ind, :]
            # Check if there are more than one with same minimum angle diff
            if len(closest) == 1:
                # Add to dict
                outDict['Link_ID'] = closest['LINK_ID'].iloc[0]
                outDict['Link_Angle'] = closest['Angle'].iloc[0]
            else:
                # Add to dict
                outDict['Link_ID'] = closest['LINK_ID'].values
                outDict['Link_Angle'] = closest['Angle'].values
        else:
            outDict['Comment'] = f'ERROR: No link found within {self.COUNT_BUFFER} of count location.'
            return outDict

        return outDict

    def loopCounts(self):
        """
            Loop through all the counts to find the closest line in the correct direction.

            Returns:
                lookup: panadas.dataframe.DataFrame
                    The lookup between the count ID and link IDs.
        """
        # Get direction for all the links
        self.calcDir()

        # Setup output list
        outLst = []
        # Loop through counts
        tot = len(self.countShp)
        for i, countRow in self.countShp.iterrows():
            outLst.append(self.lookupCount(countRow))
            print(f'\rDone {i+1} out of {tot}' + ' '*30, end='\r')

        # Convert out list to dataframe
        self.lookup = pd.DataFrame(outLst, columns=['Count_ID', 'Count_Direction', 'Link_ID',
                                            'Link_Angle', 'Comment'])

        return self.lookup.copy()

##### MAIN #####
if __name__ == '__main__':
    # Setup arguments
    parser = ArgumentParser(description=('Module to find the closest link for each count and '
                                        'provide a lookup between the count ID and link ID'))
    parser.add_argument('counts', type=filePath, help='Path to counts shapefile')
    parser.add_argument('links', type=filePath, help='Path to links shapefile')
    # Parse arguments
    args = parser.parse_args()

    # Read files
    print('Reading shapefiles')
    countLook = CountLookup(args.counts, args.links)
    print('\tDone')

    # Find the closest link for each count
    print('Finding counts')
    lookup = countLook.loopCounts()
    print('\tDone')

    # Output lookup to csv
    out = outpath(args.counts, 'Lookup', filetype='csv')
    print(f'Writing lookup to csv: {out}')
    outputCsv(lookup, out)
    print('\tDone')


