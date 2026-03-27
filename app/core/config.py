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
    loitering_windows: list[LoiteringWindow] = Field(default_factory=list)


class GeneralConfig(BaseModel):
    model_path: str = "data/models/best.pt"
    conf_threshold: float = 0.5


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
