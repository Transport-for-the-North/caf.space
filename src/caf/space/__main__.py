"""Main module."""
from __future__ import annotations
# Built-Ins
import argparse
import dataclasses
import os
from pathlib import Path
import sys

# Third Party
from caf.toolkit import LogHelper, ToolDetails

# Local Imports
from caf.space import inputs, ui, __version__, zone_translation
import caf.toolkit as ctk


def _create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for running translation with a config."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    subparsers = parser.add_subparsers(
        title="Caf.fleet model sub-commands",
        description="List of all available sub-commands",
    )

    spatial_inputs = ctk.arguments.ModelArguments(zone_translation.SpatialZoningTranslationInputs)  # noqa: F821
    spatial_inputs.add_subcommands(
        subparsers,
        "spatial",
        add_arguments=False,
        help="Create a zone translation using area based weighting using a config",
        formatter_class=ctk.arguments.TidyUsageArgumentDefaultsHelpFormatter,
    )
    
    weighted_inputs = ctk.arguments.ModelArguments(zone_translation.WeightedZoningTranslationInputs)  # noqa: F821
    weighted_inputs.add_subcommands(
        subparsers,
        "weighted",
        add_arguments=False,
        help="Create a zone translation using data based weighting from a lower zoning using a config.",
        formatter_class=ctk.arguments.TidyUsageArgumentDefaultsHelpFormatter,
    )
    weighted_inputs.add_arguments(
        "--out_path",
        type=Path,
        help="Path the translation will be saved in.",
        default=None,
        required=False,
    )

    parser.add_argument(
        "--mode",
        type=str,
        help="Mode to run translation in; spatial, weighted or GUI.",
        default="GUI",
        required=False,
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="path to config file containing parameters",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--out_path",
        type=Path,
        help="Path the translation will be saved in.",
        default=None,
        required=False,
    )

    return parser


def _parse_args() -> tuple[inputs.ZoningTranslationInputs|None, Path]:
    """Parse and validate command-line arguments.

    Returns
    -------
    Parameters for the run, with `.run()` method.
    """
    parser = _create_parser()

    # Print help if no arguments are given
    args = parser.parse_args(None if len(sys.argv[1:]) > 0 else ["-h"])  # noqa: F821

    parameters = args.dataclass_parse_func(args)
    if not isinstance(parameters, (inputs.ZoningTranslationInputs, None)):
        raise NotImplementedError(f"Config must be a subclass of {type(inputs.ZoningTranslationInputs)} or None")  # noqa: F821
    return parameters

@dataclasses.dataclass
class SpaceArguments:
    """Command Line arguments for running space."""

    config: inputs.ZoningTranslationInputs|None
    out_path: Path

    @classmethod
    def parse(cls) -> SpaceArguments:
        """Parse command line argument."""
        parser = _create_parser()

        parsed_args = parser.parse_args()
        return SpaceArguments(parsed_args.config, parsed_args.out_path)

    def validate(self):
        """Raise error for invalid input."""
        if self.out_path:
            if not self.out_path.is_dir():
                raise FileNotFoundError(f"{self.out_path} does not exist.")

def main():
    """Entry-point for caf.space.

    Raises
    ------
    ValueError
        if a translation config is not provided when required
    """
    args = SpaceArguments.parse()
    args.validate()
    out_path = args.out_path
    ver = __version__
    details = ToolDetails("caf.space", ver[:5])
    if out_path:
        log_out = out_path
    else:
        log_out = Path(os.getcwd())
    with LogHelper(__package__, details, log_file=log_out / "SPACE.log"):
        if args.config is None:
            ui.SpaceUI()
        else:
            args.config.run(args)
        


if __name__ == "__main__":
    main()


