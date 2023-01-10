from caf.space import ZoningTranslationInputs, ZoneTranslation
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
LOG_FILE = "Zone_Translation.log"

def test_run(config_path: Path):
    config = ZoningTranslationInputs.load_yaml(config_path)
    LOG.info("Config read in successfully. Running translation.")
    trans = ZoneTranslation(config)
    LOG.info(f"Translation completed, saving to output({config.output_path}) and cache({config.cache_path}).")
    if config.method == None:
        f_name = f"{config.zone_1.name}_{config.zone_2.name}"
    else:
        f_name = f"{config.zone_1.name}_{config.zone_2.name}_{config.method}"
    for path in [config.output_path, config.cache_path]:
        full_path = path / f_name
        full_path.mkdir(exist_ok=True, parents = True)
        trans.zone_translation.to_csv(full_path / f"{config.run_date}.csv")
        config.save_yaml(full_path / f"{config.run_date}_config.yml")
    LOG.info(f"Translation complete.")

if __name__=="__main__":
    test_run("caf.space/test.yml")