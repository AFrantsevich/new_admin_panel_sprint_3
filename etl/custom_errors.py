from psycopg.errors import (
    DataError,
    IntegrityError,
    NotSupportedError,
    ProgrammingError,
)

from elasticsearch.exceptions import ApiError, SerializationError, TransportError
from psycopg import OperationalError
from redis.exceptions import ConnectionError


conn_errors = (
    IntegrityError,
    DataError,
    ProgrammingError,
    NotSupportedError,
    SerializationError,
    ApiError,
)

db_errors = (
    TransportError,
    OperationalError,
    ConnectionError,
)
