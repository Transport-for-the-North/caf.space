import caf.space as cs
from pathlib import Path

def test_run(config_path: Path):
    config = cs.inputs.ZoningTranslationInputs.load_yaml(config_path)
    trans = cs.zone_translation.ZoneTranslation(config)
    trans.zone_translation.to_csv(config.output_path)

if __name__=="__main__":
    test_run("test.yml")
