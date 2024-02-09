"""
	Script to filter one shapefile based on another.
"""
##### IMPORTS #####
from argparse import ArgumentParser
import geopandas as gpd
import sys

# Script modules
from utils import filePath, outpath, TimeTaken

##### FUNCTIONS #####
def filterShapefile(inputShp, filterShp, buffer):
    """
        Filters inputShp based on what intersects with the polygon
        (or MultiPolygon) given by producing buffer of filterShp.

        Parameters:
        - inputShp: geopandas.geodataframe.GeoDataFrame
            The GeoDataFrame to be filtered, geometry type should be LineString.
        - filterShp: geopandas.geodataframe.GeoDataFrame
            The GeoDataFrame to be used as a filter.
        - buffer: int
            The amount of buffer to use on filterShp for checking whether inputShp is within filterShp.
    """
    # Get inputShp columns
    inCols = inputShp.columns.tolist()
    # Create polygons using given buffer, but keep as dataframe for join
    filterShp = gpd.GeoDataFrame({'geometry':filterShp.buffer(buffer)}, crs=filterShp.crs)

    # Do a spatial join to get only the input links that intersect with filterShp
    filtered = gpd.sjoin(inputShp, filterShp, how='inner', op='intersects')
    # Drop the extra columns added by the join and drop duplicate rows
    subCols = [i for i in inCols if i != 'geometry'] # Geometry column isn't hashable so can't check if it is identical for duplicates
    filtered = filtered.loc[:, inCols].drop_duplicates(subCols)

    return filtered

def filter(inputPath, filterPath, buffer, outPath):
    """ Filter the inputPath shapefile with the given filterPath using the given buffer. """
    # Start timer
    timer = TimeTaken()
    done = lambda: print('\tDone in', timer.getLapTime(newLap=True))

    print(f'Filtering {inputPath} with {filterPath} using {buffer:,}m buffer.')
    # Read shapefiles
    print('Reading shapefiles')
    inputShp = gpd.read_file(inputPath)
    filterShp = gpd.read_file(filterPath)
    done()

    # Filter shapefile
    print(f'Filtering shapefile, {len(inputShp):,} input links and {len(filterShp):,} filter links')
    filtered = filterShapefile(inputShp, filterShp, buffer)
    print(f'\t{len(filtered):,} links after filtering')
    done()

    # Save shapefile
    print(f'Saving filtered shapefile {outPath}')
    filtered.to_file(outPath)
    done()

    return outPath, filtered

##### MAIN #####
if __name__ == '__main__':
    # Setup parser
    parser = ArgumentParser(description='Script for filtering the ITN network based on another network.')
    parser.add_argument('input', type=filePath,
                        help='Path to input shapefile')
    parser.add_argument('filter', type=filePath,
                        help='Path to the filter shapefile')
    parser.add_argument('buffer', type=int,
                        help='Radius of buffer')
    # Get arguments
    args = parser.parse_args()

    # Start timer
    timer = TimeTaken()

    # Get path for saving
    outPath = outpath(args.input, 'FILTERED')

    filter(args.input, args.filter, args.buffer, outPath)

    print('Finished, total time', timer.getTimeTaken())