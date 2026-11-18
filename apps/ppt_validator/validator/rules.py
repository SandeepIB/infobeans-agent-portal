"""FROZEN — Legacy rule loader."""
import yaml
from pathlib import Path

RULES_FILE = Path(__file__).parent.parent / "rules.yaml"


def load_rules() -> dict:
    if RULES_FILE.exists():
        return yaml.safe_load(RULES_FILE.read_text()) or {}
    return {}
