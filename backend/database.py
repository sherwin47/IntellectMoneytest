# backend/database.py

import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Text,
    DateTime,
)
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

# --- Database Setup ---
load_dotenv()
# Render provides DATABASE_URL; otherwise, it falls back to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./intellectmoney.db")

engine_args = {}
if not DATABASE_URL.startswith("postgresql"):
    # This argument is only needed for SQLite
    engine_args["connect_args"] = {"check_same_thread": False}

# This is the single, correct engine creation
engine = create_engine(DATABASE_URL, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



# --- Database Models ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # NEW: Relationship to financial plans
    # This links a user to all the plans they own.
    financial_plans = relationship("FinancialPlan", back_populates="owner")


class FinancialPlan(Base):
    __tablename__ = "financial_plans"
    id = Column(Integer, primary_key=True, index=True)
    # User's input
    income = Column(Float, nullable=False)
    expenses = Column(Float, nullable=False)
    savings = Column(Float, nullable=False)
    risk_tolerance = Column(String, nullable=False)
    # Generated output
    ai_summary = Column(Text, nullable=True)
    recommendations_json = Column(Text, nullable=True)
    portfolio_json = Column(Text, nullable=True)
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Link to the user who owns this plan
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="financial_plans")


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

# Note: The password functions (verify_password, get_password_hash) have been
# moved to backend/auth.py to keep our code organized.