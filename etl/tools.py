import logging
import time
from contextlib import contextmanager
from dataclasses import asdict
from functools import wraps
from typing import Generator, Tuple

import psycopg
from psycopg import ClientCursor, Connection as _pg_connection
from psycopg.rows import dict_row

from config import PostgreSettings, postgres_config


def backoff(
    conn_errors: Tuple,
    db_errors: Tuple,
    start_sleep_time=0.1,
    factor=2,
    border_sleep_time=10,
):
    """
    Функция для повторного выполнения функции через некоторое время, если возникла ошибка.
    Использует наивный экспоненциальный рост времени повтора (factor)
    до граничного времени ожидания (border_sleep_time)

    Формула:
        t = start_sleep_time * (factor ^ n), если t < border_sleep_time
        t = border_sleep_time, иначе
    :param start_sleep_time: начальное время ожидания
    :param factor: во сколько раз нужно увеличивать время ожидания на каждой итерации
    :param border_sleep_time: максимальное время ожидания
    :return: результат выполнения функции
    """

    def func_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            t = start_sleep_time
            count = 1
            while t < border_sleep_time:
                try:
                    return func()
                except db_errors as database_errors:
                    logging.critical(database_errors, exc_info=True)
                    raise database_errors
                except conn_errors as connection_errors:
                    time.sleep(t)
                    t = t * factor**count
                    count += 1
                    logging.warning(connection_errors, exc_info=True)
                except Exception as ex:
                    logging.critical(ex, exc_info=True)
                    raise ex

        return inner

    return func_wrapper


@contextmanager
def pg_context(config: PostgreSettings) -> Generator[_pg_connection, None, None]:
    conn = psycopg.connect(**postgres_config.model_dump())  # pyright: ignore[]
    conn.row_factory = dict_row  # pyright: ignore[]
    conn.cursor_factory = ClientCursor
    try:
        yield conn
    finally:
        conn.close()
