"""
    The class for analysing the SATURN and ITN shapefiles in order to create the lookup between the two.
"""

##### IMPORTS #####
import os
import sys
from multiprocessing import Pool
import warnings

import geopandas as gpd
import matplotlib as mpl
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from shapely.geometry import MultiLineString, MultiPoint, Point, Polygon
from shapely.geometry.linestring import LineString
from tqdm import tqdm

# Script modules
from utils import (
    TimeTaken,
    alphaShape,
    arrowCoords,
    calcLengthDiff,
    calculateAngle,
    closestLine,
    getCoords,
    getSingleLine,
    overlapLength,
    pointToTuple,
)


##### CLASS #####
class SaturnItnLookup:
    """Class to read in SATURN and ITN shapefiles and find the corresponding links between the two."""

    # Default Buffer Values
    BUFFERS = {"overlap": 25, "withinFlat": 5, "withinRound": 1, "itnFilter": 100}
    ITN_BOUNDARY = ["convex", 1000]
    # Default ouput column names
    OUTPUT_COLS = [
        "SATURN_Link_ID",
        "ITN_Link_ID",
        "ITN_Overlap_Length(m)",
        "ITN_SAT_Angle",
        "Method",
        "StartNode",
        "EndNode",
        "StartLink",
        "EndLink",
        "Comment",
    ]
    # Default input column names
    SATURN_INPUT_COLS = {"Anode": "A", "Bnode": "B", "LINK_ID": None, "LENGTH": None}
    ITN_INPUT_COLS = {"LINK_ID": "link_id", "LENGTH": None, "SPEED": None, "TIME": None}
    # Default value for chunk size
    CHUNKSIZE = None
    # What column to use as the weights
    WEIGHT_COL = "LENGTH"
    # Values for which zone numbers are between, inclusive
    ZONE_CONNECTORS = [np.inf, np.inf]
    BRITISH_GRID_CRS = "EPSG:27700"

    def __init__(self, satPath, itnPath, resultsPath, findLinks=True, **kwargs):
        """Read in shapefiles or read results for checking if findLinks is False."""
        # Print paths
        d = {
            "SATURN Shapefile": satPath,
            "ITN Shapefile": itnPath,
            "Output CSV": resultsPath,
        }
        lst = ["{} = {}".format(k, v) for k, v in d.items()]
        print("\tPaths:", *lst, sep="\n\t\t")
        # Set results paths
        self.resultsPath = resultsPath
        # Update any defaults
        self.updateVariables(**kwargs)
        # Read shapefiles
        self.readShapefiles(satPath, itnPath, findLinks=findLinks)

        # Check whether to read the output file
        if not findLinks:
            if not os.path.exists(self.resultsPath):
                print("{} does not exist, finishing.".format(self.resultsPath))
                sys.exit(0)
            else:
                self.outputDf = pd.read_csv(self.resultsPath, usecols=self.OUTPUT_COLS)
                for i in ("Start", "End"):
                    c = "{}Node".format(i)
                    self.outputDf[c] = self.outputDf[c].apply(self.str2Tup)
        return

    def updateVariables(self, **kwargs):
        """Updates the instance variables with given values. Kwargs must be lowercase."""

        # Function for checking type
        def typeCheck(val, t):
            if not type(val) is t:
                raise TypeError(
                    "{} variable should be type {} but is {}".format(val, t, type(val))
                )

        # Function for updating int
        def upInt(default, new):
            return int(new)

        def upStr(default, new):
            return str(new)

        # Function for updating dictionary
        def upDict(default, new):
            typeCheck(new, dict)
            for i in default.keys():
                if i in new.keys():
                    default[i] = new[i]
            return default

        # Function for updating lists
        def upList(default, new):
            typeCheck(new, list)
            for i, val in enumerate(new):
                try:
                    default[i] = val
                except IndexError:
                    break
            return default

        # Variable dict
        varDict = {
            **dict.fromkeys(("buffers", "saturn_input_cols", "itn_input_cols"), upDict),
            **dict.fromkeys(("itn_boundary", "zone_connectors"), upList),
            "weight_col": upStr,
            "chunksize": upInt,
        }

        # Update any variables given
        for key, func in varDict.items():
            new = kwargs.get(key.lower(), None)
            default = getattr(self, key.upper())
            if not new is None:
                setattr(self, key.upper(), func(default, new))

        # Print paramters
        lst = ["{} = {}".format(k.upper(), getattr(self, k.upper())) for k in varDict]
        print("\tParameters:", *lst, sep="\n\t\t")

        return

    def readShapefiles(self, satPath, itnPath, findLinks=True):
        """Read the SATURN and ITN shapefiles and and some coloumns to the GeoDataFrames, return SATURN and ITN network dataframes and weighted ITN graph."""
        # Importing ITN & SATURN shapefiles into Geopandas DataFrame
        self.itnNet = gpd.read_file(itnPath)
        self.satNet = gpd.read_file(satPath)

        for shp in (self.itnNet, self.satNet):
            if any(shp.has_z):
                shp.geometry = shp.geometry.map(linestring_2D)

        if self.SATURN_INPUT_COLS["LINK_ID"] is None:
            # Convert A/B node columns to numbers
            for i in ("Anode", "Bnode"):
                nm = self.SATURN_INPUT_COLS.get(i, i)
                self.satNet[nm] = pd.to_numeric(self.satNet[nm], downcast="integer")

        for shp, cols, path in (
            ("itnNet", "ITN_INPUT_COLS", itnPath),
            ("satNet", "SATURN_INPUT_COLS", satPath),
        ):
            shp_file = getattr(self, shp)
            shp_crs = shp_file.crs
            if shp_crs is None:
                print(f"Cannot determine CRS for {path}")
            elif shp_crs != self.BRITISH_GRID_CRS:
                warnings.warn(
                    f"Invalid CRS ({shp_crs}), expected "
                    f"{self.BRITISH_GRID_CRS}, for {path}"
                )
                shp_file.to_crs(self.BRITISH_GRID_CRS, inplace=True)
            else:
                print(f"Correct CRS ({shp_crs}) given for {path}")

            for k, val in getattr(self, cols).items():
                if val is None:
                    continue

                columns = shp_file.columns.tolist()
                if val not in columns:
                    raise KeyError(
                        "Column containing {} data named {} is not present "
                        "in {}, found columns {}".format(k, val, path, columns)
                    )

        # Rename and filter columns
        flipDict = lambda d: {v: k for k, v in d.items()}
        self.itnNet = self.itnNet.rename(columns=flipDict(self.ITN_INPUT_COLS))
        self.satNet = self.satNet.rename(columns=flipDict(self.SATURN_INPUT_COLS))

        # Add link id column
        if self.SATURN_INPUT_COLS["LINK_ID"] is None:
            self.satNet["LINK_ID"] = (
                self.satNet.Anode.astype(str) + "_" + self.satNet.Bnode.astype(str)
            )
        # Calculate lengths if not provided
        if self.SATURN_INPUT_COLS["LENGTH"] is None:
            self.satNet["LENGTH"] = self.satNet.geometry.length
        if self.ITN_INPUT_COLS["LENGTH"] is None:
            self.itnNet["LENGTH"] = self.itnNet.geometry.length

        # Check if LINK_ID column is unique
        for key, val in {
            "satNet": "SATURN_INPUT_COLS",
            "itnNet": "ITN_INPUT_COLS",
        }.items():
            dups = getattr(self, key)["LINK_ID"].duplicated().sum()
            idCol = getattr(self, val)["LINK_ID"]
            if dups > 0:
                raise ValueError(
                    f"{dups:,} duplicated LINK_IDs found in {idCol} for {key}"
                )

        # Initialise other columns and variables required for finding ITN links
        if findLinks:
            # Get the start and end coordinates for links in the ITN and SATURN networks
            self.itnNet["Vertices"] = self.itnNet.geometry.apply(getCoords, args=(0, ))
            self.itnNet["Vertices2"] = self.itnNet.geometry.apply(getCoords, args=(-1, ))
            self.satNet["Vertices"] = self.satNet.geometry.apply(getCoords, args=(0, ))
            self.satNet["Vertices2"] = self.satNet.geometry.apply(getCoords, args=(-1, ))

            # Create the itn boundaries
            self.createBoundaries()

            try:
                # Calculate time if not provided
                if self.ITN_INPUT_COLS["TIME"] is None and self.WEIGHT_COL == "TIME":
                    self.itnNet["TIME"] = self.itnNet["LENGTH"] / self.itnNet["SPEED"]
                # Create the weight column for the ITN to use for shortest path, use WEIGHT * 1e6 as weight for ITN links outside the buffer
                self.itnNet[self.WEIGHT_COL] = self.itnNet[self.WEIGHT_COL].astype(
                    float
                )
                self.itnNet["WEIGHT"] = self.itnNet[self.WEIGHT_COL] * 1e6
            except KeyError as e:
                print("Column {} is missing from ITN shapefile.".format(e))
                raise
            # Create the tuples for use a graph nodes
            for i in ("Vertices", "Vertices2"):
                self.itnNet["{}_Tup".format(i)] = self.itnNet[i].apply(pointToTuple)
                self.satNet["{}_Tup".format(i)] = self.satNet[i].apply(pointToTuple)

            # Create the weighted ITN graph
            self.itnGraph = nx.DiGraph()
            self.itnGraph.add_weighted_edges_from(
                self.itnNet[["Vertices_Tup", "Vertices2_Tup", "WEIGHT"]].values
            )

        return self.satNet, self.itnNet

    def createBoundaries(self):
        """Create two polygons for the boundaries of the ITN layer in order to add warnings to links outside."""
        print(
            "\tCreating boundary using {} with -{}m buffer.".format(*self.ITN_BOUNDARY)
        )
        # Create MultiLineString of the whole ITN
        multi = self.itnNet.geometry.tolist()

        # Check which type of boundary to use for the ITN layer
        if self.ITN_BOUNDARY[0] == "convex":
            # Get boundary of itn layer
            self.itnBoundary = MultiLineString(multi).convex_hull
        elif self.ITN_BOUNDARY[0] == "concave":
            # Create MultiPoints of the whole ITN
            pointsArr = np.array([j for i in multi for j in i.coords])
            # Round points and drop duplicates
            uniques, index = np.unique(np.round(pointsArr), axis=0, return_index=True)
            pointsArr = pointsArr[index]
            # Create multipoint object
            points = MultiPoint(pointsArr)
            # Calculate alpha_shape for the points iterating through different alpha values
            for i in range(5000, 20000, 1000):
                print("\t\t\tTrying with alpha = {}".format(i))
                try:
                    concaveHull, edgePoints = alphaShape(points, i)
                    break
                except (AttributeError, ValueError) as e:
                    print("\t\t{} - {}".format(i, e))
                    continue
            else:
                raise ValueError("Could not find an concave boundary")
            # Set shape as boundary
            self.itnBoundary = concaveHull
        elif os.path.isfile(self.ITN_BOUNDARY[0]):
            # Check if shapefile is given
            if not self.ITN_BOUNDARY[0].lower().endswith(".shp"):
                raise IOError(
                    "File given is not a shapefile, {}".format(self.ITN_BOUNDARY[0])
                )
            # Read shapefile
            shp = gpd.read_file(self.ITN_BOUNDARY[0])
            # Check if there is only 1 feature
            if len(shp) != 1:
                raise ValueError(
                    "Shapefile {} has {} features expected 1".format(
                        self.ITN_BOUNDARY[0], len(shp)
                    )
                )
            # Check if it is a polygon
            shp = shp.geometry.iloc[0]
            if not type(shp) is Polygon:
                raise TypeError(
                    "Shapefile {} has feature {} expected Polygon".format(
                        self.ITN_BOUNDARY[0], type(shp)
                    )
                )
            # Use provided shapefile as boundary
            self.itnBoundary = shp
        else:
            raise ValueError(
                "ITN_BOUNDARY should be 'convex', 'concave' or the path to a shapefile with a single polygon."
            )

        # Get area close to edge of ITN layer
        self.itnEdgeArea = self.itnBoundary.difference(
            self.itnBoundary.buffer(-1 * self.ITN_BOUNDARY[1])
        )

        # Change matplotlib backend as it was causing an issue with multiprocessing
        mpl.use("agg")
        # Create the figure
        fig, ax = plt.subplots()
        plt.subplots_adjust(
            top=0.95, bottom=0.01, right=0.99, left=0.01, hspace=0, wspace=0
        )
        # Set axis paramters
        ax.set(adjustable="datalim", aspect=1)
        ax.tick_params(
            axis="both",
            which="both",
            bottom=False,
            top=False,
            right=False,
            left=False,
            labelbottom=False,
            labeltop=False,
            labelright=False,
            labelleft=False,
        )
        ax.set_title("ITN Boundary Areas")
        # Plot ITN layer
        linCol = [np.array(i.coords) for i in multi]
        linCol = LineCollection(
            linCol, label="ITN Links", color="black", linewidth=0.1, zorder=0
        )
        ax.add_collection(linCol)
        # Plot boundaries
        ax.fill(
            self.itnBoundary.exterior.xy[0],
            self.itnBoundary.exterior.xy[1],
            color="blue",
            alpha=0.5,
            label="ITN Area",
            zorder=5,
        )
        itnEdge = self.itnEdgeArea
        ax.fill(
            itnEdge.exterior.xy[0] + itnEdge.interiors[0].xy[0],
            itnEdge.exterior.xy[1] + itnEdge.interiors[0].xy[1],
            alpha=0.5,
            color="red",
            label="ITN Edge ({}m)".format(self.ITN_BOUNDARY[1]),
            zorder=10,
        )
        l = ax.legend(fontsize="small")
        l.set_zorder(20)
        # Save figure
        path = self.resultsPath.replace(".csv", "_ITN_Boundary.png")
        print("\t\tSaving ITN boundary image:", path)
        fig.savefig(path, dpi=300)
        plt.close("all")

        return

    @staticmethod
    def str2Tup(toTup):
        if not type(toTup) is str:
            return toTup
        toTup = toTup.strip()[1:-1]
        tup = [int(i) for i in toTup.split(",")]
        return tuple(tup)

    @staticmethod
    def calcAngle(satLink, itnLink):
        """Calculate the angle between two links."""
        # Calculate vectors for both links
        try:
            line1 = [satLink.Vertices_Tup, satLink.Vertices2_Tup]
            line2 = [itnLink.Vertices_Tup, itnLink.Vertices2_Tup]
            return calculateAngle(line1, line2)
        except ValueError as e:
            err = (
                f"Model Link: {satLink.LINK_ID}, Lookup Link: {itnLink.LINK_ID}. "
                + str(e)
            )
            raise ValueError(err)

    def compareDirections(self, satLink, itnLinks):
        """Compares the direction of a SATURN link with two ITN links, returns the ITN link closest to the same direction."""
        angles = []
        errors = []
        # Calculate the angles
        for i, link in enumerate(itnLinks):
            try:
                angles.append((i, self.calcAngle(satLink, link)))
            except ValueError as e:
                errors.append((i, e))

        # Check how many angles were found without errors
        if len(angles) == 1:
            return itnLinks[angles[0][0]]
        elif len(angles) > 1:
            # Convert list to array
            arr = np.array(angles)
            # Find minimum angle and get the indices from the first column
            # where the second column is equal to the minimum angle
            minAng = arr.min(axis=0)[1]
            i = arr[(arr.T[1] == minAng)].T[0]
            # Check if more than one link is found with the minimum angle
            if len(i) > 1:
                raise ValueError("{} ITN links found with same angle.".format(len(i)))
            else:
                # Return the itnLink
                return itnLinks[int(i)]
        else:
            for i in errors:
                print(i[1])
            raise ValueError("Could not find angle between either ITN.")

    def findItnNode(self, satNode, itnLinks):
        """Find the closest ITN node within 1m, if there isn't any return None."""
        # Find nodes
        itnNodes = pd.Series(pd.concat([itnLinks.Vertices_Tup, itnLinks.Vertices2_Tup]).unique())
        itnNodes = gpd.GeoSeries(itnNodes.apply(Point))
        ind = itnNodes.within(satNode.buffer(1))
        # Check how many are found
        if ind.sum() < 1:
            return None
        elif ind.sum() == 1:
            return pointToTuple(itnNodes.loc[ind].iloc[0])
        else:
            dist = itnNodes.loc[ind].distance(satNode)
            ind = dist.loc[dist == dist.min()]
            if ind.sum() != 1:
                print("Oh Crap!")
                raise ValueError("Too many nodes found with the same minimum distance")
            return pointToTuple(itnNodes.loc[ind].iloc[0])

    def overlapLen(self, satLink, itnLink):
        """Calculate the length of the ITN link that overlaps the SATURN link."""
        return overlapLength(satLink, itnLink, self.BUFFERS["overlap"])

    def checkItnEdge(self, satLink):
        """Check if a SATURN link intersects with the edge area."""
        # If it is complete within boundary don't produce warning
        if satLink.geometry.within(self.itnBoundary):
            return ""
        elif satLink.geometry.intersects(self.itnEdgeArea):
            return "WARNING: SATURN link is within {}m of the edge of the ITN layer".format(
                self.ITN_BOUNDARY[1]
            )
        else:
            return ""

    def findItnLinks(self, satLink):
        """Find the ITN links that correspond to the single SATURN link."""
        # Check if tuple given
        if type(satLink) is tuple:
            satLink = satLink[1]

        outLst = []
        # Put all the code in a try statement so if any error occurs that isn't handled
        # A row containing the error can be returned for this link but then the program can continue
        try:
            # Check if the satLink is outside the itn boundary
            if not satLink.geometry.intersects(self.itnBoundary):
                outLst.append(
                    {
                        "SATURN_Link_ID": satLink.LINK_ID,
                        "Comment": "ERROR: SATURN link outside of ITN area",
                    }
                )
                return satLink.LINK_ID, outLst

            # Get list of ITN links that intersect the SATURN link
            ins = self.itnNet.intersects(
                satLink.geometry.buffer(self.BUFFERS["itnFilter"])
            )
            itnIns = self.itnNet[ins]

            # Loop through the ITN links that intersect this SATURN link
            linksWithin = []
            for iItn, itnLink in itnIns.iterrows():
                # Check if SATURN link is completely within ITN link
                if satLink.geometry.within(
                    itnLink.geometry.buffer(self.BUFFERS["withinRound"])
                ) or satLink.geometry.within(
                    itnLink.geometry.buffer(self.BUFFERS["withinFlat"], cap_style=2)
                ):
                    # Add to list
                    linksWithin.append(itnLink)

            # Check if saturn link is found within any ITN
            length = len(linksWithin)
            method = "Within {}".format(length)
            if length == 1:
                # Create dict for adding row
                row = {
                    "SATURN_Link_ID": satLink.LINK_ID,
                    "ITN_Link_ID": linksWithin[0].LINK_ID,
                    "Method": method,
                    "ITN_Overlap_Length(m)": self.overlapLen(satLink, linksWithin[0]),
                    "ITN_SAT_Angle": self.calcAngle(satLink, linksWithin[0]),
                    "Comment": self.checkItnEdge(satLink),
                }
                # Add data to outLst
                outLst.append(row)
            elif length >= 2:
                try:
                    itnLink = self.compareDirections(satLink, linksWithin)
                    # Create dict for adding row
                    row = {
                        "SATURN_Link_ID": satLink.LINK_ID,
                        "ITN_Link_ID": itnLink.LINK_ID,
                        "Method": method,
                        "ITN_Overlap_Length(m)": self.overlapLen(satLink, itnLink),
                        "ITN_SAT_Angle": self.calcAngle(satLink, itnLink),
                        "Comment": self.checkItnEdge(satLink),
                    }
                except ValueError as e:
                    # Add error data to row
                    row = {
                        "SATURN_Link_ID": satLink.LINK_ID,
                        "Method": method,
                        "Comment": "AngleError: {}".format(e),
                    }
                # Add row to list
                outLst.append(row)

            else:  # Use shortest path to find ITN links if there are not links within
                # Find the closest ITN link to each saturn end
                nodes = []
                links = []
                numFound = []
                for vert in ("Vertices", "Vertices2"):
                    # See if an ITN node is within 1m of the SATURN node
                    n = self.findItnNode(satLink[vert], itnIns)
                    if not n is None:
                        nodes.append(n)
                        links.append("None")
                    else:
                        # If no node is found find the closest ITN link
                        closest, num = closestLine(satLink[vert], itnIns)
                        numFound.append(num)
                        # Check how many links with the same minimum length have been found
                        if num == 1:
                            nodes.append(closest.iloc[0][vert + "_Tup"])
                            links.append(closest.iloc[0].LINK_ID)
                        elif num > 1:
                            try:
                                # Check which link closer to SATURN direction
                                itnLink = self.compareDirections(
                                    satLink, (closest.iloc[0], closest.iloc[1])
                                )
                                nodes.append(itnLink[vert + "_Tup"])
                                links.append(itnLink.LINK_ID)
                            except ValueError as e:
                                nodes.append(None)
                                links.append(e)
                        else:
                            nodes.append(None)
                            links.append(None)

                # Update weights for ITN links that interesect with the SATURN link buffer
                tmpGraph = self.itnGraph.copy()
                tmpGraph.add_weighted_edges_from(
                    itnIns[["Vertices_Tup", "Vertices2_Tup", self.WEIGHT_COL]].values
                )
                # Find the shortest path in the ITN network
                method = "ShortestPath - {}".format(numFound)
                path = None
                try:
                    # If either nodes value is None then raise an index error so it can be added to csv
                    if nodes[0] is None or nodes[1] is None:
                        raise IndexError("start/end nodes not found in ITN network!")
                    # Find shortest path
                    path = nx.shortest_path(
                        tmpGraph, nodes[0], nodes[1], weight="weight"
                    )
                except nx.NetworkXNoPath as e:
                    comment = "NoPathError: No path in the ITN network found."
                    row = {
                        "SATURN_Link_ID": satLink.LINK_ID,
                        "Method": method,
                        "StartNode": nodes[0],
                        "EndNode": nodes[1],
                        "StartLink": links[0],
                        "EndLink": links[1],
                        "Comment": "{} {}".format(comment, self.checkItnEdge(satLink)),
                    }
                    outLst.append(row)
                except IndexError as e:
                    comment = "ERROR: {}".format(e)
                    row = {
                        "SATURN_Link_ID": satLink.LINK_ID,
                        "Method": method,
                        "Comment": "{} {}".format(comment, self.checkItnEdge(satLink)),
                    }
                    # Try to add nodes values to row
                    try:
                        row["StartNode"] = nodes[0]
                        row["EndNode"] = nodes[1]
                    except IndexError:
                        pass
                    # Try to add links values to row
                    try:
                        row["StartLink"] = links[0]
                        row["EndLink"] = links[1]
                    except IndexError:
                        pass
                    outLst.append(row)

                # Append the links to the path
                for n in range(len(path) - 1):
                    itnLink = self.itnNet[
                        (self.itnNet.Vertices_Tup == path[n])
                        & (self.itnNet.Vertices2_Tup == path[n + 1])
                    ]
                    # If there is more than one link in the list then sort it and find the link
                    # with the lowest value in the weight column, in case there are multiple links
                    # with the same endpoints
                    if len(itnLink) > 1:
                        itnLink = itnLink.sort_values(self.WEIGHT_COL)
                    itnLink = itnLink.iloc[0]
                    comment = self.checkItnEdge(satLink)
                    # Try to calculate the angle
                    try:
                        angle = self.calcAngle(satLink, itnLink)
                    except ValueError as e:
                        comment += f", AngleError:{e}"
                        angle = np.nan
                    # Create row of data
                    row = {
                        "SATURN_Link_ID": satLink.LINK_ID,
                        "ITN_Link_ID": itnLink.LINK_ID,
                        "Method": method,
                        "StartNode": nodes[0],
                        "EndNode": nodes[1],
                        "StartLink": links[0],
                        "EndLink": links[1],
                        "ITN_SAT_Angle": angle,
                        "Comment": comment,
                    }
                    # Calculate overlap distance
                    row["ITN_Overlap_Length(m)"] = self.overlapLen(satLink, itnLink)
                    # Add data to outLst
                    outLst.append(row)

        except Exception as e:
            row = {"SATURN_Link_ID": satLink.LINK_ID, "Comment": f"ERROR: {e}"}
            outLst.append(row)
        finally:
            return satLink.LINK_ID, outLst

    @staticmethod
    def checkResults(res):
        # Add row to explain that no ITN links are found
        if len(res[1]) == 0:
            return [{"SATURN_Link_ID": res[0], "Comment": "ERROR: No ITN Links found!"}]
        else:
            return res[1]

    def loopSatLinks(self, processes=1):
        """Loop through all the SATURN links finding ITN links for each one."""
        # Check processes is int
        processes = int(processes)
        if processes < 1:
            raise ValueError("processes must be >= 1")

        if self.SATURN_INPUT_COLS["LINK_ID"] is None:
            # Check that both A node and B node are not within zone number range
            # To remove any zone connectors
            self.ZONE_CONNECTORS.sort()
            self.satNet = self.satNet[
                (
                    (self.satNet.Anode < self.ZONE_CONNECTORS[0])
                    | (self.satNet.Anode > self.ZONE_CONNECTORS[1])
                )
                & (
                    (self.satNet.Bnode < self.ZONE_CONNECTORS[0])
                    | (self.satNet.Bnode > self.ZONE_CONNECTORS[1])
                )
            ]

        # Setup variables
        tot = len(self.satNet)
        loopTimer = TimeTaken()
        outputLst = []
        print(
            "Looping through all ({:,}) of the links in the SATURN network".format(tot)
        )

        try:
            if processes > 1:
                # Create pool
                pool = Pool(processes=processes)
                count = 0
                # Calculate chunksize if it isn't given
                if self.CHUNKSIZE is None:
                    chunkSize = int(tot / processes)
                else:
                    chunkSize = int(self.CHUNKSIZE)
                # Cap chunksize
                maxChunk = 5000
                chunkSize = maxChunk if chunkSize > maxChunk else chunkSize
                # Process chunks
                print(
                    "Using {} processes with a chunksize of {}".format(
                        processes, chunkSize
                    )
                )
                pbar = tqdm(desc="Processing Links", total=tot, unit=" links")
                for res in pool.imap_unordered(
                    self.findItnLinks, self.satNet.iterrows(), chunksize=chunkSize
                ):
                    count += 1
                    if count >= chunkSize:
                        # Update progress bar and reset count
                        pbar.update(count)
                        count = 0
                    outputLst += self.checkResults(res)
                # Close progress bar just in case
                pbar.close()
            else:
                # Method without multiprocessing
                for iSat, satLink in tqdm(
                    self.satNet.iterrows(),
                    desc="Processing Links",
                    unit=" links",
                    total=tot,
                ):
                    # Find itn links
                    res = self.findItnLinks(satLink)
                    # Add current results to output list
                    outputLst += self.checkResults(res)
        finally:
            # Convert outputLst to dataframe
            self.outputDf = pd.DataFrame(columns=self.OUTPUT_COLS, data=outputLst)
        return self.outputDf

    def compareLengths(self):
        """
        Adds a column to the ouputDf that contains the lengths of the SATURN links and returns it,
        also returns a dataframe comparing the SATURN length to the total ITN overlap lengths.
        """
        # Add SATURN length column
        self.outputDf = self.outputDf.merge(
            self.satNet[["LINK_ID", "LENGTH"]],
            left_on="SATURN_Link_ID",
            right_on="LINK_ID",
            how="left",
            validate="many_to_one",
        )
        self.outputDf = self.outputDf.drop("LINK_ID", axis=1).rename(
            columns={"LENGTH": "SATURN_Length(m)"}
        )
        # Reorganise columns
        cols = [i for i in self.OUTPUT_COLS]
        cols.insert(2, "SATURN_Length(m)")
        self.outputDf = self.outputDf[cols]

        # Get length comparison
        groupCol = "SATURN_Link_ID"
        lengthCols = {"SATURN_Length(m)": "first", "ITN_Overlap_Length(m)": "sum"}
        lengthComp = calcLengthDiff(
            self.outputDf[[groupCol, *lengthCols.keys()]], groupCol, lengthCols
        )

        return self.outputDf, lengthComp

    def plotLinks(self, satLinkId):
        """Plot the SATURN link given and the corresponding ITN links that have been found."""
        if satLinkId not in self.outputDf.SATURN_Link_ID.tolist():
            print("Link ID {} not found".format(satLinkId))
            return
        # Get saturn link
        satLink = self.satNet.loc[
            self.satNet.LINK_ID == satLinkId, ["geometry", "LENGTH"]
        ].iloc[0]
        # Convert to LineString
        satLink.loc["geometry"] = getSingleLine(satLink.geometry)
        # Get corresponding ITN links and the overlap length
        itnLinks = self.outputDf.loc[
            self.outputDf.SATURN_Link_ID == satLinkId
        ].reset_index(drop=True)

        # Create the figure
        fig, ax = plt.subplots()

        # Set axis paramters
        ax.set(adjustable="datalim", aspect=1)
        ax.tick_params(
            axis="both",
            which="both",
            bottom=False,
            top=False,
            right=False,
            left=False,
            labelbottom=False,
            labeltop=False,
            labelright=False,
            labelleft=False,
        )
        plt.subplots_adjust(
            top=0.95, bottom=0.01, right=0.99, left=0.01, hspace=0, wspace=0
        )
        plt.title("ITN Links Found")

        # Plot saturn link with arrow at the end
        color = "C0"
        x, y, dx, dy, hw, hl = arrowCoords(satLink.geometry, 50, 60)
        ax.arrow(
            x,
            y,
            dx,
            dy,
            color=color,
            ec=color,
            head_width=hw,
            overhang=0,
            head_length=hl,
            length_includes_head=True,
            zorder=0,
        )
        ax.plot(
            satLink.geometry.xy[0],
            satLink.geometry.xy[1],
            color,
            linewidth=5,
            label="Sat Link: {}, {:0.1f}m".format(satLinkId, satLink["LENGTH"]),
            zorder=0,
        )

        # Plot each ITN link
        count = 0
        for i, link in itnLinks.iterrows():
            if not (
                link.Comment is None or link.Comment is np.nan or link.Comment == ""
            ):
                print(link.Comment)
            # Check if ITN link column is not blank
            if (
                link.ITN_Link_ID is None
                or link.ITN_Link_ID is np.nan
                or link.ITN_Link_ID == ""
            ):
                continue
            # Get itn link
            try:
                itnLink = self.itnNet.loc[
                    self.itnNet.LINK_ID == link.ITN_Link_ID, "geometry"
                ].iloc[0]
                itnLink = getSingleLine(itnLink)
            except IndexError as e:
                raise ValueError(f"Cannot find {link.ITN_Link_ID} in the shapefile")
            color = "C{}".format((i % 9) + 1)
            # Plot ITN link with arrow at the end
            x, y, dx, dy, hw, hl = arrowCoords(itnLink, 20, 30)
            ax.arrow(
                x,
                y,
                dx,
                dy,
                color=color,
                ec=color,
                head_width=hw,
                overhang=1.0,
                head_length=hl,
                length_includes_head=True,
                zorder=5,
            )
            ax.plot(
                itnLink.xy[0],
                itnLink.xy[1],
                color,
                zorder=5,
                label="ITN: {}, {:0.1f}m".format(
                    link.ITN_Link_ID, link["ITN_Overlap_Length(m)"]
                ),
            )
            # Count number plotted
            count += 1
        print(f"{count} lookup links plotted")

        # Plot the start and end nodes for the shortest path search
        if type(itnLinks.iloc[0]["Method"]) is str:
            if itnLinks.iloc[0]["Method"].startswith("ShortestPath"):
                for i in ("StartNode", "EndNode"):
                    mark = "+" if i == "StartNode" else "X"
                    tup = itnLinks.iloc[0][i]
                    if not type(tup) == tuple or len(tup) != 2:
                        break
                    ax.scatter(
                        tup[0], tup[1], color="black", marker=mark, label=i, zorder=10
                    )

        # Add legend and show plot
        l = ax.legend(fontsize="small")
        l.set_zorder(20)
        plt.show()
        return


##### FUNCTIONS #####
def linestring_2D(line: LineString) -> LineString:
    """Converts a 3D LineString into 2D by removing Z coordinate.

    Parameters
    ----------
    line : LineString
        Shapely LineString object with Z coordinate.

    Returns
    -------
    LineString
        LineString with just X and Y coordinates.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"line should be 'LineString' not '{type(line).__name__}'")
    if not line.has_z or line.is_empty:
        return line
    return LineString([xy[:2] for xy in line.coords])
