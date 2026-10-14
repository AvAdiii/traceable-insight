from pathlib import Path

import yaml

from ti import config

DEFAULT = config.DATA_DIR / "programme" / "thresholds.yaml"


def load(path: Path = DEFAULT) -> dict:
    return yaml.safe_load(Path(path).read_text())
