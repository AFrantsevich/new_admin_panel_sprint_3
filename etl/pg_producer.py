from config import CHUNK_SIZE
from tools import _pg_connection


class PostgresProducer:
    def __init__(self, pg_conn: _pg_connection) -> None:
        self.pg_conn = pg_conn
        self.cursor = self.pg_conn.cursor()
        self.chunk_size = CHUNK_SIZE

    def get_first_mod_time(self, table_name):
        row = self.cursor.execute(
            f"SELECT modified FROM content.{table_name} ORDER BY modified LIMIT 1;"  # pyright: ignore[]
        ).fetchall()
        return row[0]["modified"]  # pyright: ignore[]

    def get_chunks(self):
        return self.cursor.fetchmany(size=self.chunk_size)

    def make_select(self, query: str) -> None:
        self.cursor.execute(query)  # pyright: ignore[]
