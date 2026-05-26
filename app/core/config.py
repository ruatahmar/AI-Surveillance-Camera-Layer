import tomllib
from pathlib import Path
from typing import Union
from pydantic import BaseModel, Field

CONFIG_PATH = Path("config.toml")

TUNABLE_SOURCE_FIELDS = {
    "conf_threshold",
    "loitering_enabled",
    "loitering_threshold",
    "loitering_windows",
    "loitering_alert_limit",
    "alert_limit_per_track",
    "alert_cooldown",
    "no_id_alert_distance",
    "alert_confirm_frames",
    "process_every_n_frames",
    "crowd_min_people",
    "crowd_min_duration",
    "green_lanyard_enabled",
    "lanyard_green_threshold",
}

TUNABLE_GENERAL_FIELDS = {
    "conf_threshold",
    "loitering_threshold",
}


class LoiteringWindow(BaseModel):
    start: str
    end: str


class SourceConfig(BaseModel):
    name: str
    source: Union[int, str]
    loitering_enabled: bool = False
    loitering_threshold: float | None = None
    loitering_windows: list[LoiteringWindow] = Field(default_factory=list)
    loitering_alert_limit: int = 1
    alert_limit_per_track: int = 1
    alert_cooldown: float = 30.0
    no_id_alert_distance: int = 150
    alert_confirm_frames: int = 3
    process_every_n_frames: int = 1
    tracker_reset_interval: int = 0
    crowd_min_people: int = 5
    crowd_min_duration: float = 15.0
    green_lanyard_enabled: bool = False
    lanyard_green_threshold: float = 0.08


class GeneralConfig(BaseModel):
    model_path: str = "data/models/best.pt"
    conf_threshold: float = 0.5
    loitering_threshold: float = 10.0


class ConfigDiff(BaseModel):
    tunable: dict[str, dict]  # source_name -> {field: new_value}
    restart_required: list[str]  # list of reasons


class Config(BaseModel):
    general: GeneralConfig = GeneralConfig()
    sources: list[SourceConfig] = []

    @classmethod
    def load_from_toml(cls, file_path: str | Path) -> "Config":
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
        return cls(**data)

    @classmethod
    def diff(cls, old: "Config", new: "Config") -> ConfigDiff:
        tunable: dict[str, dict] = {}
        restart_required: list[str] = []

        # Check general restart fields
        if old.general.model_path != new.general.model_path:
            restart_required.append(f"model_path changed: {old.general.model_path!r} → {new.general.model_path!r}")

        # Check general tunable fields
        general_tunable: dict = {}
        for field in TUNABLE_GENERAL_FIELDS:
            old_val = getattr(old.general, field)
            new_val = getattr(new.general, field)
            if old_val != new_val:
                general_tunable[field] = new_val
        if general_tunable:
            tunable["__general__"] = general_tunable

        # Index old sources by name
        old_sources = {s.name: s for s in old.sources}
        new_sources = {s.name: s for s in new.sources}

        added = set(new_sources) - set(old_sources)
        removed = set(old_sources) - set(new_sources)

        for name in added:
            restart_required.append(f"source added: {name!r}")
        for name in removed:
            restart_required.append(f"source removed: {name!r}")

        for name, new_src in new_sources.items():
            if name not in old_sources:
                continue
            old_src = old_sources[name]

            # Check source restart fields
            if old_src.source != new_src.source:
                restart_required.append(f"source {name!r} URL/index changed")
                continue

            # Check tunable fields
            source_tunable: dict = {}
            for field in TUNABLE_SOURCE_FIELDS:
                old_val = getattr(old_src, field)
                new_val = getattr(new_src, field)
                if old_val != new_val:
                    source_tunable[field] = new_val
            if source_tunable:
                tunable[name] = source_tunable

        return ConfigDiff(tunable=tunable, restart_required=restart_required)


def get_config() -> Config:
    if CONFIG_PATH.exists():
        return Config.load_from_toml(CONFIG_PATH)
    return Config()