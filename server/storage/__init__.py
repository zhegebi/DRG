import pathlib

from sqlmodel import create_engine, Session

from ..config import DB_DIR, DB_FILE
from .tables import SQLModel

engine = None

def init_db():
    global engine
    if pathlib.Path(DB_DIR).exists() is False:
        pathlib.Path(DB_DIR).mkdir(parents=True)
    engine = create_engine(f"sqlite:///{DB_DIR}/{DB_FILE}")
    SQLModel.metadata.create_all(engine)
