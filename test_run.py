from caf.space import ZoningTranslationInputs, ZoneTranslation
from pathlib import Path
import logging

LOG = logging.getLogger(__name__)
# LOG_FILE = "Zone_Translation.log"

def test_run(config_path: Path):
    config = ZoningTranslationInputs.load_yaml(config_path)
    trans = ZoneTranslation(config)
    if config.method == None:
        f_name = f"{config.zone_1.name}_{config.zone_2.name}"
    else:
        f_name = f"{config.zone_1.name}_{config.zone_2.name}_{config.method}"
    for path in [config.output_path, config.cache_path]:
        trans.zone_translation.to_csv(path / f_name / f"{config.run_date}.csv")
        config.save_yaml(path / f_name / f"{config.run_date}_config.yml")

if __name__=="__main__":
    test_run("caf.space/test.yml")