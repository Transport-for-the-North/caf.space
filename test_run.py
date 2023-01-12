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
    LOG.info(f"Translation complete.")
    return trans

if __name__=="__main__":
    test_run("caf.space/test.yml")