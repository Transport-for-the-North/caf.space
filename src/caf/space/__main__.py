"""Main module."""

# Built-Ins
import os
from pathlib import Path

# Third Party
from caf.toolkit import LogHelper, ToolDetails

# Local Imports
import caf.space


def main():
    """Entry-point for caf.space.

    Raises
    ------
    ValueError
        if a translation config is not provided when required
    """
    args = caf.space.inputs.SpaceArguments.parse()
    args.validate()
    out_path = args.out_path
    ver = caf.space.__version__
    details = ToolDetails("caf.space", ver[:5])
    if out_path:
        log_out = out_path
    else:
        log_out = Path(os.getcwd())
    with LogHelper(__package__, details, log_file=log_out / "SPACE.log"):
        if args.mode == "GUI":
            caf.space.SpaceUI()
        elif not args.config_path:
            raise ValueError(f"For a {args.mode} translation a config is required.")
        else:
            config = caf.space.ZoningTranslationInputs.load_yaml(args.config_path)
            trans = caf.space.ZoneTranslation(config)
            if args.mode == "spatial":
                trans.spatial_translation().to_csv(
                    args.out_path / f"{config.zone_1.name}_{config.zone_2.name}_spatial.csv"
                )
            else:
                trans.weighted_translation().to_csv(
                    args.out_path
                    / f"{config.zone_1.name}_{config.zone_2.name}_{config.method}.csv"
                )


if __name__ == "__main__":
    main()
