"""
Utililty functions for the SATURN ITN comparison script.
"""
##### IMPORTS #####
from shapely.ops import unary_union, polygonize, triangulate, linemerge
from shapely.geometry import (
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    LineString,
    Point,
)
import geopandas as gpd
import numpy as np
import os
import time
import argparse
import pandas as pd
import logging, logging.handlers
import queue
from warnings import warn

##### CLASS #####
class Loggers:
    """
    Class containing methods to create the main parent logger and any child loggers.
    """

    LOGGER_NAME = "SAT_ITN_COMP"
    QUEUE = queue.Queue(-1)

    def __init__(self, logFile):
        """Creates the main logger."""
        # Initiate logger
        self.logger = logging.getLogger(self.LOGGER_NAME)
        self.logger.setLevel(logging.DEBUG)
        # Create queuehandler
        qh = logging.handlers.QueueHandler(self.QUEUE)
        self.logger.addHandler(qh)

        # Create file handler
        fh = logging.FileHandler(logFile)
        fh.setLevel(logging.DEBUG)
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # Create formatter
        format = logging.Formatter(
            "%(asctime)s [%(name)-20.20s] [%(levelname)-8.8s] %(message)s"
        )
        fh.setFormatter(format)
        ch.setFormatter(logging.Formatter("[%(levelname)-8.8s] %(message)s"))

        # Create queue listener
        self.listener = logging.handlers.QueueListener(
            self.QUEUE, fh, ch, respect_handler_level=True
        )

        # Start listener
        self.listener.start()

        self.logger.info("Initialised main log file")

        return

    def __enter__(self):
        """Called when initialising class with 'with' statement."""
        return self

    def __exit__(self, excepType, excepVal, traceback):
        """Called when exiting with statement."""
        # Write exception to logfile
        if excepType != None or excepVal != None or traceback != None:
            self.logger.critical("Oh no a critical error occurred", exc_info=True)
        else:
            self.logger.info("Program completed without any fatal errors")
        # Closes logger
        self.logger.info("Closing log file")
        self.listener.stop()
        logging.shutdown()
        return

    @classmethod
    def childLogger(klass, loggerName):
        """Creates a child logger."""
        # Initialise logger
        logger = logging.getLogger(f"{klass.LOGGER_NAME}.{loggerName}")

        return logger


class TimeTaken:
    """
    Simple class for measuring the time taken for a program to run and outputting it in a readable way.
    """

    def __init__(self):
        """Sets start to currect time when class is instanciated."""
        self.start = time.time()
        self.laps = [self.start]
        return

    def _readableTime(self, timeVal):
        """Returns a readable formatted string of the given time."""
        # If the timeVal is not a number return ??
        try:
            timeVal = float(timeVal)
        except (TypeError, ValueError) as e:
            return "?? secs."

        if timeVal >= 60:
            timeValSecs = int(timeVal % 60)
            timeValMins = int((timeVal - timeValSecs) / 60)
            if timeValMins >= 60:
                timeValMins = int(timeValMins % 60)
                timeValHrs = int((timeVal - (timeValMins * 60) - timeValSecs) / 3600)
                return "{} hrs, {} mins, {} secs.".format(
                    timeValHrs, timeValMins, timeValSecs
                )
            else:
                return "{} mins, {} secs.".format(timeValMins, timeValSecs)
        elif timeVal < 1:
            return "< 1 sec."
        else:
            return "{:.0f} secs.".format(timeVal)

    def getTimeTaken(self):
        """Returns a readable formatted string of the time taken."""
        # Calc time taken
        timeTaken = round(time.time() - self.start)
        return self._readableTime(timeTaken)

    def resetStart(self):
        """Resets the start time and the laps list, returns new start time."""
        self.start = time.time()
        self.laps = [self.start]
        return self.start

    def newLap(self):
        """Adds current time to laps list, returns list."""
        self.laps.append(time.time())
        return self.laps

    def avgLapTime(self, newLap=False):
        """Calculates the average time taken each lap."""
        # Create a newLap if option is True
        if newLap:
            self.newLap()
        # If there is only one value in laps then return None
        if len(self.laps) <= 1:
            return None
        # Get the time taken for each lap
        timeTaken = []
        for i, val in enumerate(self.laps):
            if i == 0:
                continue
            timeTaken.append(val - self.laps[i - 1])
        # Calculate average
        return sum(timeTaken) / len(timeTaken)

    def getLapTime(self, lapIndex=-1, newLap=False):
        """Returns the time of a single lap, given by lapIndex, in a readable format."""
        if newLap:
            self.newLap()
        return self._readableTime(self.laps[lapIndex] - self.laps[lapIndex - 1])

    def remainingTime(self, remainingLaps, newLap=False):
        """Returns the remaining time in a readable format when given the number of laps left."""
        avgLap = self.avgLapTime(newLap)
        if avgLap == None:
            return self._readableTime(None)
        # Calculate time left in this lap
        # get absolute value so if this lap is > avgLap it adds time on to time left
        remainingLap = abs(avgLap - (time.time() - self.laps[-1]))
        timeLeft = avgLap * remainingLaps + remainingLap
        return self._readableTime(timeLeft)


##### FUNCTIONS #####
def alphaShape(points, alpha):
    """
    Compute the alpha shape (concave hull) of a set
    of points.
    @param points: Iterable container of points.
    @param alpha: alpha value to influence the
        gooeyness of the border. Smaller numbers
        don't fall inward as much as larger numbers.
        Too large, and you lose everything!

    Source found: https://gist.github.com/dwyerk/10561690#gistcomment-2819818
    """
    if len(points) < 4:
        # When you have a triangle, there is no sense
        # in computing an alpha shape.
        return MultiPoint(list(points)).convex_hull

    tri = triangulate(points)
    triangles = np.array([i.exterior.coords for i in tri])
    a = (
        (triangles[:, 0, 0] - triangles[:, 1, 0]) ** 2
        + (triangles[:, 0, 1] - triangles[:, 1, 1]) ** 2
    ) ** 0.5
    b = (
        (triangles[:, 1, 0] - triangles[:, 2, 0]) ** 2
        + (triangles[:, 1, 1] - triangles[:, 2, 1]) ** 2
    ) ** 0.5
    c = (
        (triangles[:, 2, 0] - triangles[:, 0, 0]) ** 2
        + (triangles[:, 2, 1] - triangles[:, 0, 1]) ** 2
    ) ** 0.5
    s = (a + b + c) / 2.0
    areas = (s * (s - a) * (s - b) * (s - c)) ** 0.5
    circums = a * b * c / (4.0 * areas)
    filtered = triangles[circums < alpha]
    if len(filtered) < 1:
        raise ValueError("Alpha value too small!")
    edge1 = filtered[:, (0, 1)]
    edge2 = filtered[:, (1, 2)]
    edge3 = filtered[:, (2, 0)]
    edge_points = np.unique(np.concatenate((edge1, edge2, edge3)), axis=0).tolist()
    m = MultiLineString(edge_points)
    triangles = list(polygonize(m))
    triangles = unary_union(triangles)
    if type(triangles) is MultiPolygon:
        raise ValueError("Found MultiPolygon instead of polygon")
    return triangles, edge_points


def outputCsv(df, path, index=False, **kwargs):
    """Write outputDf to csv."""
    while True:
        try:
            df.to_csv(path, index=index, **kwargs)
            break
        except PermissionError as e:
            print(e)
            input("Please close the file and press enter...")
    return


def arrowCoords(lineString, maxWidth, maxLen, lineLen=1000):
    """Returns x, y, dx and dy coordinates for an arrow at the end of a given line string."""
    x, y = lineString.coords[-2]
    dx, dy = np.array(lineString.coords[-1]) - np.array(lineString.coords[-2])
    # Calculate headwidth and headlength
    length = lineString.length
    hw = (length / lineLen) * maxWidth
    hl = (length / lineLen) * maxLen
    # Cap the head size at maximums
    hw = hw if hw < maxWidth else maxWidth
    hl = hl if hl < maxLen else maxLen
    return x, y, dx, dy, hw, hl


def filePath(path, argErr=True):
    """Checks if given path is file and returns it if it is."""
    if os.path.isfile(path):
        return path
    # Raise error
    msg = f"{path} is not a file, or does not exist."
    if argErr:
        raise argparse.ArgumentTypeError(msg)
    else:
        raise FileNotFoundError(msg)


def outpath(path, end, filetype=""):
    """Adds end to the end of path before the filetype."""
    loc = path.rfind(".")
    if loc == -1:
        outPath = path
    else:
        outPath = path[:loc]
        if filetype == "":
            filetype = path[loc:]
    # Add period to filetype
    if not filetype.startswith("."):
        filetype = "." + filetype
    outPath += f"_{end}{filetype}"

    return outPath


def getDataFrame(val, **kwargs):
    """Check if val is a DataFrame, if not it reads the path."""
    if not isinstance(val, pd.DataFrame):
        val = pd.read_csv(val, **kwargs)
    return val


def calculateAngle(line1, line2, directed=False):
    """
    Calculate the angle between two links.

    Parameters:
        line1, line2: list-like containing tuple
            Tuples for start and end coordinates of each line.
        directed: bool
            Whether the angle returned should be between 0 and 180 (False)
            or between 0 and 360 (True). Default False.
    Returns:
        Angle between the two lines provided in degrees.
    """
    # Calculate vectors for both links
    vec = lambda x: np.array(x[1], dtype=np.float64) - np.array(x[0], dtype=np.float64)
    vectors = []
    vectors.append(vec(line1))
    vectors.append(vec(line2))
    # Check if either of the vectors are 0, 0
    for i, val in enumerate(vectors):
        if (val == 0).all():
            raise ValueError(f"Line {i+1} has vector 0, 0")

    # Normalise each vector
    normalised = []
    for val in vectors:
        norm = val / np.hypot(val[0], val[1])
        normalised.append(norm)

    # Calculate dot product
    dot = np.dot(normalised[0], normalised[1])
    # Check if dot > 1
    if abs(dot) > 1:
        dot = np.trunc(dot)

    # Calculate the angle between the two
    with np.errstate(all="raise"):
        try:
            # Round to 5dp to remove rounding error
            angle = np.round(np.degrees(np.arccos(dot)), 5)
        except Exception as e:
            print(
                e,
                "vector 1 {}, vector 2 {}, dot {}, normalised vectors {}".format(
                    *vectors, dot, normalised
                ),
            )
            return np.nan
    # Check which angle to use
    if directed:
        # Get perpendicular vector to vector 1 by rotating it 90 degrees counter clockwise
        # Flip the x and y coordinates and negate the y to rotate CCW 90 degrees
        vec1, vec2 = normalised
        perpVec1 = np.array([-vec1[1], vec1[0]])
        # Get the dot product
        dot = np.dot(perpVec1, vec2)
        # If the dot product is positive then the vectors are < 90 degrees apart
        # Which means the angle between vectors 1 and 2 is negative (or the larger angle is between 180 and 360)
        if dot > 0:
            angle = 360 - angle

    return angle


def getCoords(line, ind, pointType=True):
    """
    Gets the coordinates from a shapely LineString object at index <<ind>>.

    Parameters:
        line: shapely.geometry.LineString or shapely.geometry.MultiLineString
            LineString to get the coordinates from, if MultiLineString will be converted
            to single LineString.
        ind: int
            Index of the coordinates in the list.
        pointType: bool
            Whether to return coordinates as shapely.geometry.Point
            (True) or as a tuple (False). Default True.
    Returns:
        point: shapely.geometry.Point or tuple
            The coordinate point at the given index.
    """
    # Attempt to convert to a single LineString object
    coords = getSingleLine(line).coords[ind]
    coords = [float(i) for i in coords]
    if pointType:
        return Point(coords)
    else:
        return tuple(coords)


def pointToTuple(point):
    """
    Convert Point object to tuple.

    Parameters:
        point: shapely.geometry.Point
            Point object to be converted
    Returns:
        point: tuple[float]
            Tuple containing the x and y coordinates
            from the Point object given.
    """
    return round(point.x), round(point.y)


def closestLine(point, lines):
    """
    Finds the closest line to a point.

    Parameters:
        point: shapely.geometry.Point
            Point to find the closest line to.
        lines: geopandas.GeoSeries or geopandas.GeoDataFrame
            The LineStrings from which to find the closest line.
    Returns:
        line, returnedNum: (LineString or GeoSeries, int)
            Line(s) which is closest to the point and the number of lines returned.
    """
    dist = lines.distance(point).round(1)
    index = dist.loc[dist == dist.min()].index
    return lines.loc[index], len(index)


def overlapLength(link1, link2, buffer):
    """
    Calculate the length of link2 that overlaps with link1.

    Parameters:
        link1, link2: pandas.Series
            Pandas series with a geometry column containing a shapely LineString object.
        buffer: int
            Radius of buffer around the object to calculate overlap of.
    Returns:
        overlap: float
            Length of the overlapping section of link1.
    """
    overlap = link1.geometry.intersection(link2.geometry.buffer(buffer, cap_style=2))
    return overlap.length


def getSingleLine(line):
    """
    Convert MultiLineString to LineString, using shapely.ops.linemerge. If
    linemerge does not create a single LineString then the coordinates of the
    line are flattened into a single list so any gaps will be filled with
    straight lines.

    Parameters:
        line: shapely.MultiLineString
            Line to convert to LineString.
    Returns:
        line: shapely.LineString
            A combination of the MultiLineString.
    """
    if isinstance(line, LineString):
        return line
    elif isinstance(line, MultiLineString):
        # Try to convert to LineString
        line = linemerge(line)
        if isinstance(line, LineString):
            return line
        else:
            # If it is still not LineString then just convert to list
            # and flatten it, this will put a straight line between any gaps
            coords = []
            for l in line:
                coords += list(l.coords)
            # Warn the user that this method is being used
            warn(
                (
                    "MultiLineString converted to LineString using list method "
                    "which may cause issues if lines are not in the correct order."
                ),
                RuntimeWarning,
            )
            return LineString(coords)
    else:
        raise ValueError(f"Expected MultiLineString got {type(line)}")


def calcLengthDiff(lookup, groupCol, lengthCols):
    """
    Groups the lookup dataframe and produces a dataframe containing
    the length difference for each group.

    Parameters:
        lookup: pandas.DataFrame
            DataFrame from which to compare lengths.
        groupCol: str
            Name of column of which to group on.
        lengthCols: dict of str, length = 2
            Key should be name of column for grouping and
            value should be the grouping method to use.
    Returns:
        lengthDiff: pandas.DataFrame
            DataFrame containing the groupCol, all the lengthCols and 2 extra columns
            containing length difference and percentage difference.
    """
    # Group dataframe
    lengthDiff = lookup.groupby(groupCol, as_index=False).agg(lengthCols)
    # Calculate differences
    cols = list(lengthCols.keys())
    lengthDiff["Length_Diff(m)"] = lengthDiff[cols[1]] - lengthDiff[cols[0]]
    lengthDiff["Length_%Diff"] = (lengthDiff[cols[1]] / lengthDiff[cols[0]]) - 1
    return lengthDiff


##### TEST #####
if __name__ == "__main__":
    # Test the calculateAngle function
    testLines = [[(0, 0), (i / 2, j / 2)] for i in range(-2, 2) for j in range(-2, 2)]
    answers = []
    for line1 in testLines:
        for line2 in testLines:
            ans, dirAns = None, None
            try:
                ans = calculateAngle(line1, line2)
                dirAns = calculateAngle(line1, line2, directed=True)
            except Exception as e:
                dirAns = str(e)
            print(f"{line1}, {line2} = {ans}, {dirAns}")
