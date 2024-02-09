"""
    SCRIPT TO FIND THE CORRESPONDENCE BETWEEN SATURN & ITN LINKS
"""
##### IMPORTS #####
import os
from argparse import ArgumentParser
from pathlib import Path

# Script modules
from saturn_itn_lookup import SaturnItnLookup
from utils import outputCsv, filePath, outpath, TimeTaken
from graphs import LengthGraph, AngleGraph
from filter import filter

##### FUNCTIONS #####


##### MAIN #####
if __name__ == "__main__":
    # Setup expected arguments
    parser = ArgumentParser(
        prog=r"src\main.py",
        description="Main module for running the ITN to SATURN correspondance analysis",
    )
    parser.add_argument(
        "itn",
        help="Path to the ITN shapefile, this is the shapefile to lookup from.",
        type=filePath,
    )
    parser.add_argument(
        "saturn",
        help="Path to the saturn link (or routes) shapefile, "
        "this is the shapefile to create the lookup to.",
        type=filePath,
    )
    parser.add_argument(
        "output",
        help="Path to the output csv file (if this already exists "
        "it won't be overwritten unless `findlinks` is set).",
    )
    parser.add_argument(
        "--findlinks",
        default=False,
        action="store_true",
        help="If given will process the inputs again even if the output csv exists",
    )
    parser.add_argument(
        "-z",
        "--zone_connectors",
        default=None,
        type=int,
        nargs=2,
        help="Ignore nodes within this range, give a minimum and maximum value.",
    )
    parser.add_argument(
        "-w",
        "--weight_col",
        default=None,
        choices=["LENGTH", "TIME"],
        help="Column to use for the weights when calculating shortest path, "
        "if using TIME a column named 'SPEED' is required in the ITN shapefile.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=None,
        help="Amount of links in each processing chunk",
    )
    parser.add_argument(
        "--processes",
        default=os.cpu_count() - 1,
        type=int,
        help="The number of processes to use when finding the link lookup.",
    )
    parser.add_argument(
        "--filter",
        default=False,
        action="store_true",
        help="If given will filter the lookup shapefile "
        "based on the input before processing.",
    )
    parser.add_argument(
        "--filter_buffer",
        default=100,
        type=int,
        help="Buffer around the input shapefile to be "
        "used for filtering the lookup shapefile.",
    )
    parser.add_argument(
        "--routes",
        default=False,
        action="store_true",
        help="If given will preprocess the routes "
        "shapefile before finding the correspondance.",
    )

    args = parser.parse_args()
    print("Starting...")

    # Check output path resolves correctly, error will be raised if it doesn't
    Path(args.output).resolve()

    if args.routes:
        raise NotImplementedError("Use the routes script separately, for now.")

    # Check if shapefiles should be analysed
    kwargs = {}
    kwargs["findLinks"] = args.findlinks
    if not os.path.exists(args.output):
        kwargs["findLinks"] = True

    # Check if parameters have been given
    for i in ("zone_connectors", "weight_col", "chunksize"):
        a = getattr(args, i, None)
        if not a is None:
            kwargs[i] = a

    # Start timer
    timer = TimeTaken()

    # Filter lookup shapefile
    if args.filter:
        itnPath = outpath(args.itn, "FILTERED")
        filter(args.itn, args.saturn, args.filter_buffer, itnPath)
    else:
        itnPath = args.itn

    # Read shapefiles
    print("Reading shapefiles")
    satLook = SaturnItnLookup(args.saturn, itnPath, args.output, **kwargs)
    print(
        "\tDone in {} Total time {}".format(
            timer.getLapTime(newLap=True), timer.getTimeTaken()
        )
    )

    if kwargs["findLinks"]:
        # Put in try statement so the dataframe if output to CSV if there is an exception
        try:
            # Loop through all the SATURN links to find the ITN links for each
            print("Looping through all SATURN links")
            satLook.loopSatLinks(processes=args.processes)
            print(
                "\tDone in {} Total time {}".format(
                    timer.getLapTime(newLap=True), timer.getTimeTaken()
                )
            )

            # Compare overlap length with SATURN link length
            print("Comparing lengths")
            outputDf, lengthComp = satLook.compareLengths()
            print(
                "\tDone in {} Total time {}".format(
                    timer.getLapTime(newLap=True), timer.getTimeTaken()
                )
            )
        except Exception as e:
            print(f"{e.__class__.__name__}: {e}")
        finally:
            # Write output df to csv
            print("Writing outputs to CSVs")
            outputCsv(satLook.outputDf, satLook.resultsPath)
            print("\t{}".format(satLook.resultsPath))
            path = (
                satLook.resultsPath[: satLook.resultsPath.rfind(".")] + "_Lengths.csv"
            )
            outputCsv(lengthComp, path)
            print("\t{}".format(path))
            print("\tDone in {}".format(timer.getLapTime(newLap=True)))

        # Create length plots
        print("Plotting length graphs")
        graph = LengthGraph(path)
        # Plot scatter
        graph.plotScatter(path=path.replace(".csv", "_Scatter"))
        # Plot hexbin
        graph.plotHex(path=path.replace(".csv", "_Hexbin"))
        print("\tDone in {}".format(timer.getLapTime(newLap=True)))
        # Create angle plots
        print("Plotting angle graphs")
        graph = AngleGraph(satLook.resultsPath)
        # Plot scatter
        graph.plotScatter(path=path.replace(".csv", "_Angle_Scatter"))
        # Plot hexbin
        graph.plotHex(path=path.replace(".csv", "_Angle_Hexbin"))
        print("\tDone in {}".format(timer.getLapTime(newLap=True)))

    else:
        # Plot any saturn links input
        while True:
            inp = input("Type a SATURN link ID to see it ")
            # Exit loop
            if inp.lower() == "exit":
                print("Exiting")
                break
            else:
                try:
                    satLook.plotLinks(inp)
                except Exception as e:
                    print(e)

    print("Finished, time taken", timer.getTimeTaken())
