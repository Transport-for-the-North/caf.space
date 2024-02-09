# SAT_ITN_Comp
Tool for analysing a SATURN network (or Journey Time Routes or similar) shapefile and an ITN shapefile (or similar) to produce a lookup between them.
**This script is still work in progress so any outputs will need checking.**

## Running Tool
Currently this tool is not an executably and as such can only be ran on a machine with Python installed. There are 3 scripts in the tool that can be ran separately (eventually these will be combined into one tool and made into an executable file).

### main.py 
Main script for performing the ITN correspondance and checking the results ran using the following parameters:
```
usage: main.py [-h] [--findlinks] [-z ZONE_CONNECTORS] [-w {LENGTH,TIME}]
               [--chunksize CHUNKSIZE] [--routes]
               itn saturn output

Main module for running the ITN to SATURN correspondance analysis

positional arguments:
  itn                   Path to the ITN shapefile
  saturn                Path to the saturn link (or routes) shapefile
  output                Path to the output csv file

optional arguments:
  -h, --help            show this help message and exit
  --findlinks           If given will process the inputs again even if the
                        output csv exists
  -z ZONE_CONNECTORS, --zone_connectors ZONE_CONNECTORS
                        Ignore nodes above this number
  -w {LENGTH,TIME}, --weight_col {LENGTH,TIME}
                        Column to use for the weights when calculating
                        shortest path
  --chunksize CHUNKSIZE
                        Amount of links in each processing chunk
  --routes              If given will preprocess the routes shapefile before
                        finding the correspondance.
```

### routes.py
```
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

### filter.py
```
usage: filter.py [-h] itn filter buffer

Script for filtering the ITN network based on another network.

positional arguments:
  itn         Path to ITN shapefile
  filter      Path to the filter shapefile
  buffer      Radius of buffer

optional arguments:
  -h, --help  show this help message and exit
```

### graphs.py
```
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
