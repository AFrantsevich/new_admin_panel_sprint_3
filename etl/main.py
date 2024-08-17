import datetime as dt
import time
from abc import abstractmethod
from typing import List

from elasticsearch import Elasticsearch
from redis import Redis

from config import POLLING_TIME, elc_config, postgres_config, redis_config
from custom_errors import conn_errors, db_errors
from elc import ELCHandler
from models import FilmWorkModel, Genre, Person
from pg_producer import PostgresProducer
from schema import schema
from storage import RedisStorage, State
from tools import backoff, pg_context


class Loader:
    """Реализация загрузчика данных полученных из postgres в elastic."""

    def __init__(self, pgproducer, elk, state: State):
        self.state = state
        self.pgproducer = pgproducer
        self.elc = elk
        self.table_name = ""

    def set_mod_time(self, table_name) -> None:
        """Метод установки самого раннего времени изменения записи.

        Используется при первичном наполнении таблицы.
        """

        if self.get_time(table_name) is None:
            modified_time = self.pgproducer.get_first_mod_time(table_name)
            self.state.set_state(
                table_name, modified_time - dt.timedelta(microseconds=1)
            )

    def get_time(self, table_name) -> str | None:
        """Конвертация datetime для записи в RedisStorage"""

        time = self.state.get_state(table_name)
        if not time:
            return None
        return time.decode("utf-8")

    @abstractmethod
    def format_data_to_bulk(self, chunk) -> List[dict]:
        """Метод конвертации данных postgres в json формат

        для переноса в elasctic. Реализуется в каждом
        конкретном загрузчике.
        """

        ...

    @abstractmethod
    def select_query(self) -> str:
        """Абстрактный метод получения sql запроса

        для выборки данных.
        """

        ...

    def load_data(self) -> None:
        """Главная функция загрузки данных из кадой конкретной таблицы

        в elastic.
        """

        self.set_mod_time(self.table_name)
        self.pgproducer.make_select(self.select_query())
        chunk = self.pgproducer.get_chunks()

        while chunk:
            self.state.set_state(self.table_name, chunk[len(chunk) - 1]["modified"])
            bulk_data = self.format_data_to_bulk(chunk)
            self.elc.load(bulk_data)
            chunk = self.pgproducer.get_chunks()


class FilmWorkLoader(Loader):
    def __init__(self, pgproducer, elk, state: State) -> None:
        super().__init__(pgproducer, elk, state)
        self.table_name = "film_work"

    def select_query(self) -> str:
        return (
            f"SELECT id,rating,title,description,modified "
            f"FROM content.{self.table_name} "
            f"WHERE modified > '{self.get_time(self.table_name)}' ORDER BY modified;"
        )

    def format_data_to_bulk(self, chunk) -> List[dict]:
        bulk_data = []
        for row in chunk:
            source = FilmWorkModel(
                imdb_rating=row.pop("rating"), id=str(row.pop("id")), **row
            )
            bulk_data.append(
                {
                    "_index": elc_config.index_name,
                    "_id": source.id,
                    "_op_type": "update",
                    "doc": source.model_dump(),
                    "doc_as_upsert": True,
                }
            )

        return bulk_data


class PersonLoader(Loader):
    def __init__(self, pgproducer, elk, state: State) -> None:
        super().__init__(pgproducer, elk, state)
        self.table_name = "person"

    def select_query(self) -> str:
        return (
            "SELECT pfw.film_work_id film_id, "
            "ARRAY_AGG (role || '*' || full_name || '*' || p.id) actors, "
            "MAX(p.modified) as modified "
            "FROM content.person_film_work pfw "
            "LEFT JOIN content.person p ON p.id = pfw.person_id "
            "GROUP BY film_id "
            f"HAVING MAX(p.modified) > '{self.get_time(self.table_name)}' "  # pyright: ignore[]
            "ORDER BY modified"
        )

    def format_data_to_bulk(self, chunk) -> List[dict]:
        bulk_data = []
        for film in chunk:
            body = {
                "directors_names": [],
                "actors_names": [],
                "writers_names": [],
                "directors": [],
                "actors": [],
                "writers": [],
            }
            for actor in film["actors"]:
                data = actor.split("*")

                body[data[0] + "s_names"].append(data[1])
                body[data[0] + "s"].append({"id": data[2], "name": data[1]})

            person = Person(**body)
            bulk_data.append(
                {
                    "_index": elc_config.index_name,
                    "_id": film["film_id"],
                    "_op_type": "update",
                    "doc": person.model_dump(),
                    "doc_as_upsert": True,
                }
            )
        return bulk_data


class GenreLoader(Loader):
    def __init__(self, pgproducer, elk, state: State):
        super().__init__(pgproducer, elk, state)
        self.table_name = "genre"

    def select_query(self) -> str:
        return (
            "SELECT gfw.film_work_id film_id, "
            "ARRAY_AGG (g.name) genres, "
            "MAX(g.modified) as modified "
            "FROM content.genre_film_work gfw "
            "LEFT JOIN content.genre g ON g.id = gfw.genre_id "
            "GROUP BY film_id "
            f"HAVING MAX(g.modified) > '{self.get_time(self.table_name)}' "
            "ORDER BY modified"
        )

    def format_data_to_bulk(self, chunk) -> List[dict]:
        bulk_data = []
        for film in chunk:
            body = {
                "genres": [],
            }
            for genre in film["genres"]:
                body["genres"].append(genre)

            person = Genre(**body)
            bulk_data.append(
                {
                    "_index": elc_config.index_name,
                    "_id": film["film_id"],
                    "_op_type": "update",
                    "doc": person.model_dump(),
                    "doc_as_upsert": True,
                }
            )
        return bulk_data


@backoff(conn_errors, db_errors)
def main() -> None:
    """Главная функция загрузки данных из кадой конкретной таблицы

    в elastic.
    """

    with pg_context(postgres_config) as connection, Redis(
        host=redis_config.host
    ) as redis_connection, Elasticsearch(elc_config.url) as elc:
        redis_storage = RedisStorage(redis_connection)
        state = State(redis_storage)

        elc_handler = ELCHandler(elc)
        elc_handler.create_index_if_not_ex(schema, elc_config.index_name)

        pg_producer = PostgresProducer(connection)

        film_work = FilmWorkLoader(pg_producer, elc_handler, state)
        person = PersonLoader(pg_producer, elc_handler, state)
        genre = GenreLoader(pg_producer, elc_handler, state)

        while True:
            film_work.load_data()
            person.load_data()
            genre.load_data()
            time.sleep(POLLING_TIME)


if __name__ == "__main__":
    main()
