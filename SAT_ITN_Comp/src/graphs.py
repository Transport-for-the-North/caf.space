"""
    Module containing class to plot the overlap length % difference of the ITN links.
"""
##### IMPORTS #####
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib import colors, style
import pandas as pd
import sys, os
from argparse import ArgumentParser

# Script modules
from utils import filePath

##### CLASSES #####
class LengthGraph:
    """ Plots the lengths scatter graph when given a dataframe or csv path. """

    # Columns expected
    DTYPES = {'SATURN_Link_ID':'str', 'SATURN_Length(m)':'float', 'ITN_Overlap_Length(m)':'float',
                'Length_Diff(m)':'float', 'Length_%Diff':'float'}
    # Plotting constants
    CMAP = plt.cm.viridis
    MARKER = 'x'
    MARKER_SIZE = 10

    def __init__(self, csv):
        # Check if path or dataframe given
        if type(csv) is str:
            # Check if file exists
            filePath(csv)
            self.df = pd.read_csv(csv, dtype=self.DTYPES, usecols=list(self.DTYPES.keys()), header=0)
        elif type(csv) is pd.DataFrame:
            self.df = csv.copy()
            # Check if there are any columns missing
            missing = []
            for i in self.DTYPES.keys():
                if not i in self.df.columns.tolist():
                    missing.append(i)
            # Raise error
            if len(missing) > 0:
                raise ValueError('Missing columns in dataframe - {}'.format(missing))
        else:
            TypeError('csv argument should be a str or pandas.DataFrame')

        return

    def update_annot(self, ind, type):
        if type.lower() == 'scatter':
            getSatLink = lambda i: self.df.iloc[i].SATURN_Link_ID
            text = "{}".format(" ".join(list(map(getSatLink, ind["ind"]))))
        elif type.lower() == 'hexbin':
            counts = self.data.get_array()[ind['ind'][0]]
            text = 'Counts = {:.0f}'.format(counts)

        pos = self.data.get_offsets()[ind["ind"][0]]
        self.annot.xy = pos
        self.annot.set_text(text)
        # annot.get_bbox_patch().set_facecolor(cmap(c[ind["ind"][0]]))
        self.annot.get_bbox_patch().set_alpha(0.4)
        return

    def hover(self, event, type):
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            cont, ind = self.data.contains(event)
            if cont:
                self.update_annot(ind, type)
                self.annot.set_visible(True)
                self.fig.canvas.draw_idle()
            else:
                if vis:
                    self.annot.set_visible(False)
                    self.fig.canvas.draw_idle()
        return

    def _formatPlot(self, cbarLabel):
        # Create colorbar
        cbar = self.fig.colorbar(self.data)
        cbar.ax.set_ylabel(cbarLabel)
        cbar.ax.zorder = 1
        # Label axis
        self._labelAxis()
        # Set up annotation
        self.annot = self.ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                                        bbox=dict(boxstyle="round", fc="w"),
                                        arrowprops=dict(arrowstyle="->"), zorder=10)
        self.annot.set_visible(False)
        return
    
    def _labelAxis(self):
        # Set axis labels
        self.ax.set_xlabel('SATURN Link Length (km)')
        self.ax.set_ylabel('Overlap Length Difference')
        self.ax.get_xaxis().set_major_formatter(FuncFormatter(lambda x, pos: '{:.0f}'.format(x / 1000)))
        self.ax.get_yaxis().set_major_formatter(FuncFormatter(lambda x, pos: '{:.0%}'.format(x)))
        return

    def plotHex(self, path=None):
        # Create plot
        self.fig, self.ax = plt.subplots()
        self.data = plt.hexbin(self.df['SATURN_Length(m)'], self.df['Length_%Diff'], gridsize=100,
                                bins='log', mincnt=1, linewidths=0.1)
        # Format plot
        self._formatPlot('Counts')

        if path is None:
            # Show figure
            self.fig.canvas.mpl_connect("motion_notify_event", lambda event: self.hover(event, 'hexbin'))
            plt.show()
        else:
            self.fig.savefig(self._checkPath(path), dpi=300)
        return

    def plotScatter(self, path=None):
        # Create colormap
        c = self.df['Length_Diff(m)'].abs()
        cmap = plt.cm.viridis
        norm = colors.LogNorm()

        # Create plot
        self.fig, self.ax = plt.subplots()
        self.data = plt.scatter(self.df['SATURN_Length(m)'], self.df['Length_%Diff'], c=c,
                                marker=self.MARKER, cmap=self.CMAP, norm=norm, s=self.MARKER_SIZE)
        # Format plot
        self._formatPlot('Abosulte Length Difference (m)')

        if path is None:
            # Show figure
            self.fig.canvas.mpl_connect("motion_notify_event", lambda event: self.hover(event, 'scatter'))
            plt.show()
        else:
            self.fig.savefig(self._checkPath(path), dpi=300)
        return

    @staticmethod
    def _checkPath(path):
        if path.lower().endswith('.png'):
            return path
        else:
            loc = path.rfind('.')
            if loc == -1:
                return path + '.png'
            else:
                return path[:loc] + '.png'

class AngleGraph(LengthGraph):
    """ Plots the angle between the SATURN and ITN links. """
    
    # Columns expected
    DTYPES = {'SATURN_Link_ID':'str', 'ITN_Link_ID':'str', 'SATURN_Length(m)':'float',
                'ITN_SAT_Angle':'float', 'ITN_Overlap_Length(m)':'float'}
    
    def _labelAxis(self):
        # Set axis labels
        self.ax.set_xlabel('SATURN Link Length (km)')
        self.ax.set_ylabel('ITN SATURN Angle ($^\circ$)')
        self.ax.get_xaxis().set_major_formatter(FuncFormatter(lambda x, pos: '{:.0f}'.format(x / 1000)))
        self.ax.get_yaxis().set_major_formatter(FuncFormatter(lambda x, pos: '{:.0f}'.format(x)))
        return
    
    def plotHex(self, path=None):
        # Create plot
        self.fig, self.ax = plt.subplots()
        self.data = plt.hexbin(self.df['SATURN_Length(m)'], self.df['ITN_SAT_Angle'], gridsize=100,
                                bins='log', mincnt=1, linewidths=0.1)
        # Format plot
        self._formatPlot('Counts')

        if path is None:
            # Show figure
            self.fig.canvas.mpl_connect("motion_notify_event", lambda event: self.hover(event, 'hexbin'))
            plt.show()
        else:
            self.fig.savefig(self._checkPath(path), dpi=300)
        return
    
    def plotScatter(self, path=None):
        # Create colormap
        c = self.df['ITN_Overlap_Length(m)']
        norm = colors.LogNorm()
        
        # Create plot
        self.fig, self.ax = plt.subplots()
        self.data = plt.scatter(self.df['SATURN_Length(m)'], self.df['ITN_SAT_Angle'], c=c,
                                marker=self.MARKER, cmap=self.CMAP, norm=norm, s=self.MARKER_SIZE)
        # Format plot
        self._formatPlot('ITN Overlap Length (m)')

        if path is None:
            # Show figure
            self.fig.canvas.mpl_connect("motion_notify_event", lambda event: self.hover(event, 'scatter'))
            plt.show()
        else:
            self.fig.savefig(self._checkPath(path), dpi=300)
        return

##### MAIN #####
if __name__ == '__main__':
    # Read arguments
    parser = ArgumentParser(description='Module for producing graphs for the SATURN to ITN script')
    parser.add_argument('-l', '--lengths', default=None, type=filePath,
                        help='Path to CSV containing length comparison data')
    parser.add_argument('-a', '--angles', default=None, type=filePath,
                        help='Path to CSV containing the angle data')
    parser.add_argument('-p', '--pltType', dest='pltType', default='save', choices=['save', 'scatter', 'hexbin'],
                        help="Type of plot to output, if 'save' then saves both plot types")
    
    # Get arguments
    args = parser.parse_args()
    
    # Check what inputs have been given
    for i in ('lengths', 'angles'):
        # Initiate class
        csv = getattr(args, i)
        if csv is None:
            continue
        if i == 'lengths':
            graph = LengthGraph(csv)
        elif i == 'angles':
            graph = AngleGraph(csv)
        
        # Produce plots
        if args.pltType == 'scatter':
            graph.plotScatter()
        elif args.pltType == 'hexbin':
            graph.plotHex()
        elif args.pltType == 'save':
            # Rename path
            loc = csv.rfind('.')
            path = csv if loc == -1 else csv[:loc]
            path += '_' + i.capitalize()
            print('Saving plots here {}'.format(path))
            # Save plots
            graph.plotScatter(path=path + '_Scatter.png')
            graph.plotHex(path=path + '_Hexbin.png')
            print('\tDone')
