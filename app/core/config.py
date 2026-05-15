import tomllib
from pathlib import Path
from typing import Union
from pydantic import BaseModel, Field

CONFIG_PATH = Path("config.toml")


class LoiteringWindow(BaseModel):
    start: str
    end: str


class SourceConfig(BaseModel):
    name: str
    source: Union[int, str]
    loitering_enabled: bool = False
    loitering_threshold: float | None = None  # Per-source override
    loitering_windows: list[LoiteringWindow] = Field(default_factory=list)
    alert_limit_per_track: int = 1  # How many alerts of each type per person session
    alert_cooldown: float = 0.0  # Minimum seconds between alerts per track
    process_every_n_frames: int = 1  # Process every Nth frame (1 = every frame)
    tracker_reset_interval: int = 0  # Seconds between tracker resets (0 = never)
    crowd_min_people: int = 5  # Min people to trigger crowd alert
    crowd_min_duration: float = 15.0  # Seconds crowd must persist before alert


class GeneralConfig(BaseModel):
    model_path: str = "data/models/best.pt"
    conf_threshold: float = 0.5
    loitering_threshold: float = 10.0  # Global default


class Config(BaseModel):
    general: GeneralConfig = GeneralConfig()
    sources: list[SourceConfig] = []

    @classmethod
    def load_from_toml(cls, file_path: str | Path) -> "Config":
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
        return cls(**data)


def get_config() -> Config:
    if CONFIG_PATH.exists():
        return Config.load_from_toml(CONFIG_PATH)
    return Config()  # Default settings
