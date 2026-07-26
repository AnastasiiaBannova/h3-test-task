import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class AreaCenterSettings(BaseSettings):
    lat: float
    lon: float


class AreaSettings(BaseSettings):
    center: AreaCenterSettings
    radius: float  # meters


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV", ".env"),
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    microservice_name: str
    debug: bool

    area: AreaSettings
    hex_resolution: int


settings = Settings()
