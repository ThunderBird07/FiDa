from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings
from app.models import *  # noqa: F401,F403

engine = create_engine(settings.DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)