import logging

from pydantic import (
    Field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(
    level=logging.DEBUG,
    filename="loader.log",
    filemode="w",
    format="%(asctime)s %(levelname)s %(message)s",
)
logging.getLogger().addHandler(logging.StreamHandler())

CHUNK_SIZE = 10
POLLING_TIME = 10


class SettingsMixin(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class PostgreSettings(SettingsMixin):
    dbname: str
    host: str
    port: int
    user: str
    password: str


class ElcSettings(SettingsMixin):
    index_name: str
    elc_host: str
    elc_port: int

    @property
    def url(self):
        return f"http://{self.elc_host}:{self.elc_port}"


class RedisSettings(SettingsMixin):
    host: str = Field(alias="redis_host")


postgres_config = PostgreSettings()  # pyright: ignore[]
elc_config = ElcSettings()  # pyright: ignore[]
redis_config = RedisSettings()  # pyright: ignore[]
