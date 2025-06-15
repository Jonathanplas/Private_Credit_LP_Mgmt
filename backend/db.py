# filepath: backend/db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
load_dotenv()

# Get database connection details from environment variables or use SQLite as fallback
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "lpmanagement")
DB_TYPE = os.getenv("DB_TYPE", "postgresql")

# Fallback to SQLite if PostgreSQL connection fails
try:
    DATABASE_URL = f"{DB_TYPE}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    engine = create_engine(DATABASE_URL)
    # Test connection
    with engine.connect():
        print("Connected to PostgreSQL database!")
except Exception as e:
    print(f"Could not connect to PostgreSQL database: {e}")
    print("Falling back to SQLite database...")
    DATABASE_URL = "sqlite:///./backend/lpmanagement.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()