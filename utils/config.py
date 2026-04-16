import yaml
from pathlib import Path

_config = None

def load_config() -> dict:
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            _config = yaml.safe_load(f)
    return _config

def get_all_sources() -> list[dict]:
    cfg = load_config()
    sources = []
    for group in cfg["sources"].values():
        sources.extend(group)
    return sources

def get_topics() -> list[dict]:
    return load_config()["topics"]

def get_topic_by_slug(slug: str) -> dict | None:
    for t in get_topics():
        if t["slug"] == slug:
            return t
    return None
