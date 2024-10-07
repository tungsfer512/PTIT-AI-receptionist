from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

current_path = os.getcwd()
database_path = os.path.join(current_path, "app", "database", "kiosk.db")
DATABASE_URL = "sqlite:///" + database_path  

engine = create_engine(
    DATABASE_URL,
    connect_args = {"check_same_thread": False}    
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
