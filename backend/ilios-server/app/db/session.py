from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import settings

engine = create_engine(settings.db_dsn, pool_pre_ping=True, max_overflow=20)

SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()
