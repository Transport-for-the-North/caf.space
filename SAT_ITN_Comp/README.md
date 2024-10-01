# SAT_ITN_Comp

Tool for analysing a SATURN network (or Journey Time Routes or similar) shapefile and an ITN shapefile (or similar) to produce a lookup between them.
**This script is still work in progress so any outputs will need checking.**

## Running Tool

Currently this tool is not an executable and as such can only be ran on a machine with Python installed. There are 3 scripts in the tool that can be ran separately (eventually these will be combined into one tool and made into an executable file).

Install Python and then install all packages from [requirements.txt](requirements.txt)
before attempting to run in any of the scripts. **The [environment.bat](environment.bat)
batch file will install Python into a new environment and activate it ready to run the
Python commands below, this requires Miniforge3 to be installed from:
[conda-forge.org/miniforge/](https://conda-forge.org/miniforge/)**

## Main

Main script ([main.py](main.py)) for performing the ITN correspondance and checking
the results ran using the following parameters:

```plaintext
usage: src\main.py [-h] [--findlinks] [-z ZONE_CONNECTORS ZONE_CONNECTORS]
                   [-w {LENGTH,TIME}] [--chunksize CHUNKSIZE]
                   [--processes PROCESSES] [--filter]
                   [--filter_buffer FILTER_BUFFER] [--routes]
                   itn saturn output

Main module for running the ITN to SATURN correspondance analysis

positional arguments:
  itn                   Path to the ITN shapefile, this is the shapefile to
                        lookup from.
  saturn                Path to the saturn link (or routes) shapefile, this is
                        the shapefile to create the lookup to.
  output                Path to the output csv file (if this already exists it
                        won't be overwritten unless `findlinks` is set).

optional arguments:
  -h, --help            show this help message and exit
  --findlinks           If given will process the inputs again even if the
                        output csv exists
  -z ZONE_CONNECTORS ZONE_CONNECTORS, --zone_connectors ZONE_CONNECTORS ZONE_CONNECTORS
                        Ignore nodes within this range, give a minimum and
                        maximum value.
  -w {LENGTH,TIME}, --weight_col {LENGTH,TIME}
                        Column to use for the weights when calculating
                        shortest path, if using TIME a column named 'SPEED' is
                        required in the ITN shapefile.
  --chunksize CHUNKSIZE
                        Amount of links in each processing chunk
  --processes PROCESSES
                        The number of processes to use when finding the link
                        lookup.
  --filter              If given will filter the lookup shapefile based on the
                        input before processing.
  --filter_buffer FILTER_BUFFER
                        Buffer around the input shapefile to be used for
                        filtering the lookup shapefile.
  --routes              If given will preprocess the routes shapefile before
                        finding the correspondance.
```

### Inputs

#### ITN File

ITN shapefile needs the following columns (with the exact names):

- 'link_id': ID column for the links in the ITN shapefile, **mandatory**
- 'SPEED': optional speed limit for the links, required if using TIME weighting.

#### SATURN Shapefile

SATURN shapefile requires the following columns:

- 'A': A node number
- 'B': B node number

#### Parameters

There are some parameters within the code which may be changed to adjust the lookup
calculations.

The following constants within the `SaturnItnLookup` class in the `saturn_itn_lookup`
module can be changed.

- `BUFFERS`: this is a Python dictionary with the following 4 buffer values (in metres)
  - 'overlap': the radius around a link used to determine the overlap distance
    (default 25m).
  - 'withinFlat': radius around an ITN link to determine whether the SATURN link is
    completely within, this value is used with a flat end radius (default 5m).
  - 'withinRound': same as above but radius also extends the ends of the link, which is
    why this value is smaller (default 1m).
  - 'itnFilter': radius around individual SATURN link to filter ITN links which will not
    be consider (for this individual link), any ITN links which intersect with this
    radius will be checked when determining the lookup (default 100m).

- `ITN_BOUNDARY`: list of parameters for calculating the ITN boundary
  1. First value is the name of the boundary method, either 'convex' or 'concave',
    'concave' will generate a tighter boundary but may cause error with sparse or
    disconnected shapefiles.
  2. Radius (in metres) to use when calculating the boundary around the ITN (default
     1000m).

### Outputs

The tool produces two output CSVs and 4 graphs.

#### Lookup CSV

This CSV will have the name given as the output argument and it contains the lookup
between the two shapefiles. The CSV contains the following columns:

- "SATURN_Link_ID": ID of the link from the SATURN shapefile (may contain duplicates
  if multiple ITN links are found for a single SATURN link).
- "ITN_Link_ID": corresponding ITN link ID.
- "SATURN_Length(m)": length of the SATURN link in metres.
- "ITN_Overlap_Length(m)": length (metres) of the ITN link found to be overlapping the
  SATURN link, overlapping is determined using a radius around the SATURN link.
- "ITN_SAT_Angle": angle between the direction of the SATURN link and the ITN link.
- "Method": method which was used to determine this links correspondence, either
  'within' or 'shortest path'.
- "StartNode": coordinates of the start point of the shortest path calculation.
- "EndNode": coordinates of the end point of the shortest path calculation.
- "StartLink": link ID used to find start of shortest path (blank if the SATURN link
  start point was close enough to an ITN node).
- "EndLink": link ID used to find end of shortest path (blank if the SATURN link
  start point was close enough to an ITN node).
- "Comment": any error message or warning.

#### Length Comparison CSV

This CSV contains a comparison between the SATURN link length and the ITN overlap length,
it will have the same name as [Lookup CSV](#lookup-csv) with "_Lengths" appended
to the file name.

- "SATURN_Link_ID": SATURN link ID.
- "SATURN_Length(m)": length of the SATURN link in metres.
- "ITN_Overlap_Length(m)": total overlap length of all corresponding ITN links.
- "Length_Diff(m)": difference (ITN - SATURN) in the SATURN link length and ITN overlap.
- "Length_%Diff": percentage difference in the SATURN link length and ITN overlap.

#### Graphs

Multiple PNG graphs are output from the process all will have the same name as
[Lookup CSV](#lookup-csv) with the graph name appended to it.

- 'ITN_Boundary': map of the ITN links with the calculated boundary around it.
- 'Lengths_Scatter': scatter plot showing the overlap length difference vs the SATURN link length.
- 'Lengths_Hexbin': hexbin plot showing the same data as 'Lengths_Scatter'.
- 'Lengths_Angle_Scatter': scatter plot showing the ITN SATURN angle vs the SATURN link length.
- 'Lengths_Angle_Hexbin': hexbin plot showing the same data as 'Lengths_Angle_Scatter'.

## Routes

Routes script ([routes.py](routes.py)) for preprocessing a journey time routes
shapefile before running [Main](#main).

```plaintext
usage: routes.py [-h] [--segmented_path SEGMENTED_PATH] [-i ID_COLUMN]
                 [-s SEGMENT] [--overwrite] [-g] [--lookup_csv LOOKUP_CSV]
                 shapefile

Script for preprocessing a routes shapefile before running the ITN
correspondance.

positional arguments:
  shapefile             Path to routes shapefile

optional arguments:
  -h, --help            show this help message and exit
  --segmented_path SEGMENTED_PATH
                        Path for the segmented shapefile. Required if using '
                        --group'
  -i ID_COLUMN, --id_column ID_COLUMN
                        Name of the column in the shapefile containing unique
                        route IDs.
  -s SEGMENT, --segment SEGMENT
                        Rough minimum value for each segment (simple
                        implementation so length can vary). Length will be in
                        CRS units.
  --overwrite           Set overwrite to false.
  -g, --group           Will regroup the segmented csv lookup file.
  --lookup_csv LOOKUP_CSV
                        Segmented CSV lookup file to be regrouped, required if
                        using '--group'.
```

### Filter

Script ([filter.py](filter.py)) for filtering one line shapefile based on another.

```plaintext
usage: filter.py [-h] itn filter buffer

Script for filtering the ITN network based on another network.

positional arguments:
  itn         Path to ITN shapefile
  filter      Path to the filter shapefile
  buffer      Radius of buffer

optional arguments:
  -h, --help  show this help message and exit
```

### Graphs

Module ([graphs.py](graphs.py)) for producing graphs for the SATURN to ITN script.

```plaintext
usage: graphs.py [-h] [-l LENGTHS] [-a ANGLES] [-p {save,scatter,hexbin}]

Module for producing graphs for the SATURN to ITN script

optional arguments:
  -h, --help            show this help message and exit
  -l LENGTHS, --lengths LENGTHS
                        Path to CSV containing length comparison data
  -a ANGLES, --angles ANGLES
                        Path to CSV containing the angle data
  -p {save,scatter,hexbin}, --pltType {save,scatter,hexbin}
                        Type of plot to output, if 'save' then saves both plot
                        types
```
