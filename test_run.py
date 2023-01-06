from caf.space import ZoningTranslationInputs, ZoneTranslation
from pathlib import Path

def test_run(config_path: Path):
    config = ZoningTranslationInputs.load_yaml(config_path)
    trans = ZoneTranslation(config)
    trans.zone_translation.to_csv(config.output_path)

if __name__=="__main__":
    test_run("caf.space/test.yml")
