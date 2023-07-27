"""Main module."""
import caf.space
from caf.toolkit import LogHelper, ToolDetails
from pathlib import Path

if __name__ == "__main__":
    args = caf.space.inputs.SpaceArguments.parse()
    args.validate()
    out_path = args.out_path
    details = ToolDetails("example", "1.0.0")
    with LogHelper("SPACE", details, out_path / "logg.log"):
        if args.mode == "GUI":
            caf.space.SpaceUI()
        elif not args.config_path:
            raise ValueError(f"For a {args.mode} translation a config is required.")
        else:
            config = caf.space.ZoningTranslationInputs.load_yaml(args.config_path)
            trans = caf.space.ZoneTranslation(config)
            if args.mode == "spatial":
                out = trans.spatial_translation().to_csv(
                    args.out_path / f"{config.zone_1.name}_{config.zone_2.name}_spatial.csv",
                    index=False,
                )
            else:
                trans.weighted_translation().to_csv(
                    args.out_path
                    / f"{config.zone_1.name}_{config.zone_2.name}_{config.method}.csv",
                    index=False,
                )
