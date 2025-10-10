import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# --- Database Setup (Upgraded for PostgreSQL) ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to a local SQLite database if the DATABASE_URL is not set
if not DATABASE_URL:
    print("INFO:     DATABASE_URL not found, falling back to local SQLite database.")
    DATABASE_URL = "sqlite:///./intellectmoney.db"

# The 'connect_args' is only needed for SQLite
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- User Database Model ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)


# --- Database Utility Functions ---
def get_db():
    """Dependency to get a DB session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_database():
    """Creates all database tables."""
    Base.metadata.create_all(bind=engine)

def verify_password(plain_password, hashed_password):
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hashes a plain password."""
    return pwd_context.hash(password)