from typing import List
from pydantic import BaseModel


class FilmWorkModel(BaseModel):
    id: str
    imdb_rating: float | None
    title: str
    description: str | None


class Directors(BaseModel):
    id: str
    name: str


class Actors(BaseModel):
    id: str
    name: str


class Writers(BaseModel):
    id: str
    name: str


class Person(BaseModel):
    directors_names: List
    actors_names: List
    writers_names: List
    directors: List
    writers: List
    actors: List


class Genre(BaseModel):
    genres: List
