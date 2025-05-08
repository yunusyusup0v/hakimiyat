import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

data = os.getenv('DATABASE')

ENGINE = create_engine(
    f'{data}',
    pool_size=50,
    max_overflow=100,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)

Base = declarative_base()
Session = sessionmaker(bind=ENGINE, autoflush=False)



def connect():
    session = Session()
    try:
        yield session
    finally:
        session.close()