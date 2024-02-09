"""
	Module for performing some post processing on the link lookup outputs.
"""

##### IMPORTS #####
import pandas as pd
import numpy as np
from argparse import ArgumentParser
from warnings import warn
import os

# Script modules
from utils import getDataFrame, outputCsv, outpath, filePath

##### Post Processing Class #####
class PostProcessing:
    """ Class for performing some post process analysis on the lookup outputs. """
    # Variables
    LOOKUP = None
    LENGTH_COMP = None

    def __init__(self, lookup_csv, length_comp):
        # Read csvs if paths given
        for i, val in (('lookup', lookup_csv), ('length_comp', length_comp)):
            setattr(self, i.upper(), getDataFrame(val, low_memory=False))

        return

    @staticmethod
    def binRanges(bins, fmt='', units=''):
        """ Loop through bins and change them to ranges instead of single numbers """
        newBins = []
        for i, val in enumerate(bins):
            if i == (len(bins)-1):
                break
            newBins.append(f'{val:{fmt}}{units} - {bins[i+1]:{fmt}}{units}')

        return newBins

    @staticmethod
    def minMaxBins(data, bins):
        """ Add min and max from data to bins. """
        bins = bins.copy()
        bins.sort()
        # Add minimum to bin at the start
        if data.min() < bins[0]:
            bins.insert(0, data.min())
        # Add max to end of bins
        max = data.max()
        if max > bins[-1]:
            bins.append(max)

        return bins

    @staticmethod
    def dataframePercentages(df):
        """ Add total column and row and calculate percentages. """
        # Calculate totals columns
        df.loc['Total', :] = df.sum(axis=0)
        df.loc[:, 'Total'] = df.sum(axis=1)
        # Calculate percentages
        perc = df / df.loc['Total', 'Total']
        return df, perc

    def lengthTable(self, startingDf=None):
        """ Create table of the length difference. """
        # Get data from dataframe
        if startingDf is None:
            startingDf = self.LENGTH_COMP
        # Get arrays from dataframe
        y = startingDf['SATURN_Length(m)']
        x = startingDf['Length_%Diff']

        # Create bins
        xbin = [-1, -0.5, -0.25, -0.2, -0.15, -0.1, -0.05, 0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.5, 1]
        ybin = [0, 100, 1000, 5000, 10000]
        # Add min and max to bins
        xbin = self.minMaxBins(x, xbin)
        ybin = self.minMaxBins(y, ybin)
        # Create histogram
        hist, xbin, ybin = np.histogram2d(x, y, bins=[xbin, ybin])

        # Convert list of bins to list of ranges
        ybin = self.binRanges(ybin, fmt=',.0f', units='m')
        xbin = self.binRanges(xbin, fmt='.0%')

        # Convert to dataframe
        df = pd.DataFrame(columns=ybin, index=xbin, data=hist)
        # Calculate totals columns and percentages
        df, perc = self.dataframePercentages(df)

        return df, perc

    def filterAngle(self, minAngle, minLenDiff):
        """
            Filter out any ITN links with angle greater than minAngle for model links
            with a greater percentage length difference than minLenDiff.
        """
        # Find links with length difference greater than minLenDiff
        cond = self.LENGTH_COMP['Length_%Diff'] > minLenDiff
        linkID = self.LENGTH_COMP.loc[cond, 'SATURN_Link_ID']
        # Find rows with greater angle and also linkID from above
        cond = (self.LOOKUP['SATURN_Link_ID'].isin(linkID)) & (self.LOOKUP['ITN_SAT_Angle'] > minAngle)
        # Use the inverse of the above condition to filter the dataframe
        filtered = self.LOOKUP.loc[~cond]
        # Reproduce LENGTH_COMP so a new lengthTable can be done
        lenComp = filtered.loc[:, ['SATURN_Link_ID', 'SATURN_Length(m)',
                                    'ITN_Overlap_Length(m)']].groupby(
                                    'SATURN_Link_ID', as_index=False).agg(
                                    {'SATURN_Length(m)':'first', 'ITN_Overlap_Length(m)':'sum'})
        # Calculate percentage difference
        lenComp['Length_%Diff'] = (lenComp.loc[:, 'ITN_Overlap_Length(m)'] / lenComp.loc[:, 'SATURN_Length(m)']) - 1
        # Check how much data was removed
        rows = len(self.LOOKUP) - len(filtered)
        cond = ~(self.LOOKUP.SATURN_Link_ID.isin(filtered.SATURN_Link_ID))
        removedLinks = self.LOOKUP.loc[cond, 'SATURN_Link_ID'].unique()
        print(f'\tFiltering removed {rows} rows and {len(removedLinks)} model link(s) completely')
        print(f'\tRemoved Links: {removedLinks}')

        return filtered, lenComp

    def addCols(self, lookupData, lookupCols, dataCols, startingDf=None):
        """ Add columns from lookupData to dataframe given, if no startingDf is given uses self.LOOKUP dataframe. """
        # If no starting dataframe given use LOOKUP
        if startingDf is None:
            startingDf = self.LOOKUP
        # Read lookup data csv
        cols = set(dataCols)
        cols.add(lookupCols[1])
        data = getDataFrame(lookupData, usecols=cols, low_memory=False)

        # Join the two dataframes
        self.merged = startingDf.merge(data, left_on=lookupCols[0], right_on=lookupCols[1],
                                    how='left', validate='many_to_one')

        return self.merged.copy()

    def jtOverlap(self, jtCols, overlapCols, lengthCols, colSuffix='overlap'):
        """ Adds a column containing the time taken for the overlapping section of the link. """
        # Dict of args to test
        args = {'overlap':overlapCols, 'length':lengthCols}
        # Check if parameters passed are acceptable
        if isinstance(jtCols, str):
            for k, v in args.items():
                assert (v is str), f'jtCols is string so {k}Cols should also be string'
            # Put the strings in a list
            jtCols = [jtCols]
            overlapCols = [overlapCols]
            lengthCols = [lengthCols]
        else:
            # Assuming jtCols is some list like object overlapCols and lengthCols should be the same length
            # or they should be a single column (str)
            if isinstance(overlapCols, str) and isinstance(overlapCols, str):
                # Put the strings in a list
                overlapCols = [overlapCols] * len(jtCols)
                lengthCols = [lengthCols] * len(jtCols)
            else:
                # Lengths of the lists should be the same
                assert (len(overlapCols) == len(lengthCols)), 'overlapCols and lengthCols should refer to the same number of columns'
                # Make lists same length as jtcols if they're 1
                if len(overlapCols) == 1:
                    overlapCols = list(overlapCols) * len(jtCols)
                    lengthCols = list(lengthCols) * len(jtCols)
                # Lists should be same length as jtCols
                assert (len(overlapCols) == len(jtCols)), 'overlapCols should be length 1 or same length as jtCols'

        addedCols = []
        # Loop through jt columns
        for jt, over, length in zip(jtCols, overlapCols, lengthCols):
            # Calculate overlap percentage round any over one down
            overlapPerc = self.merged.loc[:, over] / self.merged.loc[:, length]
            overlapPerc.loc[overlapPerc > 1] = np.floor(overlapPerc)
            # Add new column
            newCol = f'{jt}_{colSuffix}'
            jtData = self.merged.loc[:, jt]
            self.merged[newCol] = jtData * overlapPerc
            addedCols.append(newCol)
            # Add overlap length column for rows with jt data
            newLen = newCol + '_length'
            self.merged[newLen] = self.merged.loc[(~jtData.isna()), over]
            addedCols.append(newLen)

        return addedCols

    @staticmethod
    def strNan(arr):
        """ Replace any nan values in the array with an empty string. """
        if arr.isna().sum() > 0:
            values = arr.values.astype(str)
            values[values=='nan'] = ''
        else:
            values = arr
        return values


    def groupCols(self, dataCols, groupCol, weightCol):
        """ Group columns of data using various functions. """
        # Define some groupby functions
        def groupVals(x):
            """ Get all the unique values in the groupby column. """
            vals = self.merged.loc[x.index, groupCol].unique().astype(str).tolist()
            string = ', '.join(vals)
            return f"'{string}'"

        new_sum = lambda x: x.sum(min_count=1)

        def weighted_mean(x):
            """ Function for calculating the weighted mean when using groupby. """
            weights = self.merged.loc[x.index, weightCol]
            # Check if x is all nan
            if np.isnan(x).all():
                return np.nan
            # Check if weights are all zero
            elif weights.sum() == 0 or np.isnan(weights.sum()):
                group = groupVals(x)
                warn(f'Cannot calculate weighted mean for {group} using mean instead.', RuntimeWarning)
                # Return average without using weighting
                return np.average(x)
            else:
                # Return weighted average
                return np.average(x, weights=weights)

        def weighted_mode(x):
            """ Function for calculating the mode using weighting when using groupby. """
            # Replace nan with empty string
            values = self.strNan(x)
            # Get unique values and the indices
            unique, indices = np.unique(values, return_inverse=True)
            # Check if more than one unique value
            if len(unique) > 1:
                # Count the number of occurences
                count = np.bincount(indices, weights=self.merged.loc[x.index, weightCol])
                # Return the value at the max
                val = unique[count == count.max()]
                if len(val) > 1:
                     # Count number of occurences without using weights
                     count = np.bincount(indices)
                     val = unique[count == count.max()]
                     # Check length of val again
                     if len(val) > 1:
                        group = groupVals(x)
                        warn(f'{len(val)} values found for the mode of group {group}, putting all values into answer.', RuntimeWarning)
                        return ' / '.join(val.astype(str))
                return val[0]
            else:
                return unique[0]

        # Replace str names of functions with actual functions in dict
        aggCols = {}
        for k, val in dataCols.items():
            if isinstance(val, str) and val.lower() in ('weighted_mean', 'weighted_mode', 'new_sum'):
                aggCols[k] = locals()[val.lower()]
            else:
                aggCols[k] = val

        # Group the lookup
        self.grouped = self.merged.groupby(groupCol, as_index=False).agg(aggCols)
        return self.grouped.copy()

    def missingData(self, dataCol, dataType, jtCol, startingDf=None):
        """ Produce tables for missing JT data. """
        if isinstance(dataCol, str):
            assert (type(dataCol) == type(dataType) and type(dataCol) == type(dataBins)), 'parameters are not the same type'
            dataCol = [dataCol]
            dataType = [dataType]
            dataBins = [dataBins]

        # Get starting dataframe
        if startingDf is None:
            startingDf = self.merged

        # Get rows with/without data
        hasData = {'Without':startingDf[jtCol].isna()}
        hasData['With'] = ~hasData['Without']
        # Loop through parameters given
        outputs = []
        for c, t in zip(dataCol, dataType):
            # Get histogram for with or without data
            dfs = []
            for i in hasData.keys():
                data = startingDf.loc[hasData[i], c]
                if t.lower() == 'number':
                    bins = [0, 100, 1000, 5000, 10000, np.inf]
                    # Check maximum
                    if data.max() > bins[-1]:
                        bins.append(data.max())
                    # Create histogram
                    hist, binEdges = np.histogram(data, bins)
                    index = self.binRanges(binEdges, fmt=',.0f', units='m')
                else:
                    # Convert any nan values to ''
                    data = self.strNan(data)
                    # Get histogram for string values
                    index, indices = np.unique(data, return_inverse=True)
                    hist = np.bincount(indices)
                # Create dataframe
                dfs.append(pd.DataFrame(index=index, data={i:hist}))

            # Combine DataFrames
            df = pd.concat(dfs, axis=1, sort=False)
            # Calculate totals columns and percentages
            df, perc = self.dataframePercentages(df)
            # Rename percentage column
            perc.columns = [f'{i} %' for i in perc.columns]

            outputs.append((df, perc))

        return outputs

##### FUNCTIONS #####
def writeLengthTable(hist, histPerc, outPath):
    """ Write the hist and histPerc dataframes given to an excel file. """
    with pd.ExcelWriter(out) as writer:
        hist.to_excel(writer, sheet_name='Counts')
        histPerc.to_excel(writer, sheet_name='Percentages')
    return

##### MAIN #####
if __name__ == '__main__':
    # Set up arguments
    parser = ArgumentParser(description='Module for running post processing on the lookup outputs')
    parser.add_argument('lookup_csv', type=filePath,
                        help='Path to the lookup csv produced.')
    parser.add_argument('length_comparison', type=filePath,
                        help='Path to the length comparison CSV produced')
    parser.add_argument('join_data', type=filePath,
                        help='Path to the csv containing the data to be joined')
    parser.add_argument('model_data', type=filePath,
                        help='Path to the csv containing model data to be joined')
    # Parse arguments
    args = parser.parse_args()

    pp = PostProcessing(args.lookup_csv, args.length_comparison)

    # Produce length table and percentages and write to excel file
    print('Creating length table')
    out = outpath(args.length_comparison, "LengthTable", filetype='.xlsx')
    writeLengthTable(*pp.lengthTable(), out)
    print('\tDone')
    # Remove any links over given angle that have a length diff above
    minLenDiff = 0.15
    for minAngle in (150, 90, 60):
        outDir = os.path.split(args.length_comparison)[0]
        outDir = os.path.join(outDir, f'Filtered_Angle_{minAngle}{os.sep}')
        os.mkdir(outDir)
        print(f'Filtering rows with minimum overlap length difference > {minLenDiff:.0%} and an angle > {minAngle}')
        filtered, filtLen = pp.filterAngle(minAngle, minLenDiff)
        # Create new length table
        out = outpath(outDir, "FilteredLengthTable", filetype='.xlsx')
        writeLengthTable(*pp.lengthTable(filtLen), out)
        print('\tDone')

        # Add ITN and JT data
        # Columns to join
        overlapCol = 'ITN_Overlap_Length(m)'
        dataCols = {**dict.fromkeys(('DESCTERM', 'NATURE', 'CLASSIFICA', 'STREETNAME'), 'weighted_mode')}
        jtCols = [f'{t} av_jt_mean' for t in ('AM', 'IP', 'PM', 'OP')]
        lengthCol = 'LNKLENGTH'

        # Add all required columns
        print('Joining ITN Data')
        joinCols = list(dataCols.keys()) + jtCols + [lengthCol]
        pp.addCols(args.join_data, ['ITN_Link_ID', 'link_id'], joinCols, startingDf=filtered)
        # Join model link data
        print('Joining Model Data')
        pp.addCols(args.model_data, ['SATURN_Link_ID', 'Link_ID'], ['REGION'], startingDf=pp.merged)
        # Calculating overlap journey times
        print('\tCalculating overlapping journey times')
        addedCols = pp.jtOverlap(jtCols, overlapCol, lengthCol)
        # Output to csv
        out = outpath(outDir, "Joined", filetype='.csv')
        print(f'\tOutputting to csv: {out}')
        outputCsv(pp.merged, out)

        # Add new cols to cols to be grouped
        dataCols[overlapCol] = 'new_sum'
        dataCols['SATURN_Length(m)'] = 'first'
        dataCols['REGION'] = 'weighted_mode'
        for i in addedCols:
            dataCols[i] = 'new_sum'
        # Grouping columns
        print('\tGrouping columns')
        grouped = pp.groupCols(dataCols, 'SATURN_Link_ID', overlapCol)
        # Output to csv
        out = outpath(outDir, "Grouped", filetype='.csv')
        print(f'\tOutputting to csv: {out}')
        outputCsv(grouped, out)
        print('\tDone')

        # Produce missing data tables for ITN links
        for k, v in {'ITNLinks':(pp.merged, 'AM av_jt_mean'), 'ModelLinks':(pp.grouped, 'AM av_jt_mean_overlap')}.items():
            dataCols = ['DESCTERM', 'REGION', 'SATURN_Length(m)']
            dataType = ['str', 'str', 'number']
            outputs = pp.missingData(dataCols, dataType, v[1], startingDf=v[0])
            out = outpath(outDir, f'MissingJTData_{k}', filetype='xlsx')
            with pd.ExcelWriter(out) as writer:
                for nm, data in zip(dataCols, outputs):
                    data[0].to_excel(writer, sheet_name=nm)
                    data[1].to_excel(writer, sheet_name=nm, startcol=len(data[0].columns)+1, index=False)
