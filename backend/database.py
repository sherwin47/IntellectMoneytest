
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


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./intellectmoney.db")

engine_args = {}
if not DATABASE_URL.startswith("postgresql"):
    
    engine_args["connect_args"] = {"check_same_thread": False}


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()





class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    
    financial_plans = relationship("FinancialPlan", back_populates="owner")


class FinancialPlan(Base):
    __tablename__ = "financial_plans"
    id = Column(Integer, primary_key=True, index=True)
    
    income = Column(Float, nullable=False)
    expenses = Column(Float, nullable=False)
    savings = Column(Float, nullable=False)
    risk_tolerance = Column(String, nullable=False)
    
    ai_summary = Column(Text, nullable=True)
    recommendations_json = Column(Text, nullable=True)
    portfolio_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="financial_plans")




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

