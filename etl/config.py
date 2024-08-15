from dataclasses import dataclass
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    filename="loader.log",
    filemode="w",
    format="%(asctime)s %(levelname)s %(message)s",
)

CHUNK_SIZE = 10
POLLING_TIME = 10


@dataclass
class PostgreConfig:
    dbname: str
    user: str
    password: str
    host: str
    port: str

    @classmethod
    def load(cls):
        return cls(
            dbname=os.environ.get("DB_NAME", "movies"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "password"),
            host=os.environ.get("DB_HOST", "db"),
            port=os.environ.get("DB_PORT", "5432"),
        )


@dataclass
class ElcConfig:
    index_name: str
    url: str

    @classmethod
    def load(cls):
        return cls(
            index_name="movies",
            url=os.environ.get("ELC_HOST", "http://elasticsearch")
            + ":"
            + os.environ.get("ELK_PORT", "9200"),
        )


@dataclass
class RedisConfig:
    host: str

    @classmethod
    def load(cls):
        return cls(host=os.environ.get("REDIS_HOST", "redis"))


postgres_config = PostgreConfig.load()
elc_config = ElcConfig.load()
redis_config = RedisConfig.load()
