from typing import List
import logging

from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import bulk


class ELCHandler:
    def __init__(self, elc: Elasticsearch) -> None:
        self._elc = elc

    def load(self, bulk_data: List[dict]):
        resp = bulk(self._elc, bulk_data)
        logging.debug(f"Добавлены записи в ELK {resp}")

    def create_index_if_not_ex(self, data, index):
        try:
            self._elc.indices.get(index=index)
        except NotFoundError:
            self._elc.indices.create(index=index, body=data)
