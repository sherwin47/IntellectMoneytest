# backend/app.py

import os
import sys
from datetime import timedelta, datetime # Ensure datetime is imported
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
import google.generativeai as genai
import json
import re
import requests
from dotenv import load_dotenv

# --- FIX FOR IMPORT ERRORS ---
# This block adds your project's root directory to the Python path
# so it can find your other modules like 'backend' and 'ml'.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
# --- END OF FIX ---

# Now, all your custom module imports will work correctly
from backend.database import get_db, create_database, User, FinancialPlan # ADD FinancialPlan HERE
from ml.fuzzy_logic import calculate_risk_profile
from typing import List
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user # ADD get_current_user HERE
)

# --- API Key Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
# Ensure the SECRET_KEY is also loaded for JWT
SECRET_KEY = os.getenv("SECRET_KEY")

if not all([GEMINI_API_KEY, NEWS_API_KEY, ALPHA_VANTAGE_KEY, SECRET_KEY]):
    raise ValueError("One or more environment variables are missing from your .env file.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')
SYSTEM_INSTRUCTION = (
    "You are an expert financial assistant for 'IntellectMoney', a service for an Indian user. "
    "Your tone must be professional, clear, and encouraging."
)
# ---

create_database()
app = FastAPI(title="IntellectMoney API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    """Serves the main index.html file."""
    return FileResponse('frontend/index.html')

# --- Pydantic Models ---
class UserCreate(BaseModel): fullname: str; email: str; password: str
class UserLogin(BaseModel): email: str; password: str
class Token(BaseModel): access_token: str; token_type: str
class UserFinancialProfile(BaseModel): income: float; expenses: float; savings: float; risk_tolerance_input: str
class RecommendationResponse(BaseModel): summary: dict; recommendations: List[str]; portfolio: dict
class ChatMessage(BaseModel): message: str
class ChatResponse(BaseModel): reply: str
class NewsArticle(BaseModel): title: str; url: str; summary: str; source: str
class MarketNewsResponse(BaseModel): articles: List[NewsArticle]
class PlanResponse(BaseModel):
    id: int
    created_at: datetime
    income: float
    expenses: float
    ai_summary: str
    recommendations_json: str
    portfolio_json: str

    class Config:
        orm_mode = True # Helps Pydantic read data from the database model

class HealthScoreResponse(BaseModel):
    score: int
    rating: str
    feedback: str



# --- Helper Function to Fetch Stock Price ---
def fetch_stock_price(symbol: str):
    api_symbol = symbol.split('.')[0]
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={api_symbol}&apikey={ALPHA_VANTAGE_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if "Note" in data:
            return "Sorry, the stock market API limit has been reached. Please try again later."
        quote = data.get("Global Quote")
        if not quote or not quote.get("05. price"):
            return f"Sorry, I found the symbol **{symbol}**, but I couldn't retrieve its price data."
        price = f"₹{float(quote['05. price']):.2f}"
        change_percent_str = quote.get('10. change percent', '0%')
        change_percent = float(change_percent_str.replace('%', ''))
        change_symbol = '▲' if change_percent >= 0 else '▼'
        return f"The current price of **{symbol}** is **{price}** ({change_symbol} {change_percent:.2f}%)."
    except Exception as e:
        print(f"Alpha Vantage API error: {e}")
        return "Sorry, I'm having trouble connecting to the stock market data service."


# --- API Endpoints ---



@app.post("/api/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password, fullname=user.fullname)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"message": "User registered successfully"}

@app.post("/api/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/chatbot", response_model=ChatResponse)
def handle_chat(message: ChatMessage):
    user_message = message.message.strip()
    intent_prompt = f"""Analyze the user's question: "{user_message}"
        Is the user asking for a stock price? Answer with ONLY the Indian stock ticker (e.g., RELIANCE.NSE) or the word "GENERAL"."""
    try:
        intent_response = model.generate_content(intent_prompt)
        classification = intent_response.text.strip()
        if "." in classification and "GENERAL" not in classification:
            return {"reply": fetch_stock_price(classification)}
        else:
            general_prompt = f"{SYSTEM_INSTRUCTION}\n\nUSER QUESTION: {user_message}"
            general_response = model.generate_content(general_prompt)
            return {"reply": general_response.text}
    except Exception as e:
        print(f"An error occurred in the chatbot logic: {e}")
        return {"reply": "Sorry, I'm having a little trouble understanding. Can you try rephrasing?"}

@app.get("/api/market-news", response_model=MarketNewsResponse)
def get_market_news():
    url = f"https://newsapi.org/v2/everything?q=finance&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") != "ok":
            raise HTTPException(status_code=500, detail="Failed to fetch news from NewsAPI.")
        articles = [{"title": a.get("title"), "url": a.get("url"), "summary": a.get("description", ""), "source": a.get("source", {}).get("name", "Unknown")} for a in data.get("articles", [])]
        return {"articles": articles}
    except Exception as e:
        print(f"An error occurred while fetching news: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market news.")

@app.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(profile: UserFinancialProfile):
    risk_mapping = {"low": 3, "medium": 5, "high": 8}
    user_risk_preference = risk_mapping.get(profile.risk_tolerance_input, 5)
    calculated_risk_score = calculate_risk_profile(income=profile.income, savings=profile.savings, user_preference=user_risk_preference)
    
    if calculated_risk_score <= 4: risk_profile_description = "Conservative Investor"
    elif calculated_risk_score <= 7: risk_profile_description = "Balanced Investor"
    else: risk_profile_description = "Growth-Oriented Investor"
    
    monthly_surplus = profile.income - profile.expenses

    prompt = f"""
    You are an expert financial advisor for an Indian user.
    Analyze the following user profile:
    <profile>
        <income>₹{profile.income:,.2f}</income>
        <expenses>₹{profile.expenses:,.2f}</expenses>
        <savings>₹{profile.savings:,.2f}</savings>
        <monthly_surplus>₹{monthly_surplus:,.2f}</monthly_surplus>
        <risk_tolerance>{profile.risk_tolerance_input}</risk_tolerance>
        <investor_type>{risk_profile_description}</investor_type>
    </profile>

    Your response MUST be in two distinct parts, marked with <advice> and <portfolio> headers.

    First, provide personalized advice under an <advice> header. This should include a summary paragraph and a bulleted or numbered list of 3-4 actionable recommendations.
    
    Second, provide a portfolio allocation under a <portfolio> header. This MUST be a single, valid JSON object with "labels" and "data" keys. The data values must sum to 100.
    """

    try:
        response = model.generate_content(prompt)
        raw_text = response.text
        print("--- AI Raw Response --- \n", raw_text, "\n-----------------------")
        
        # --- NEW ROBUST PARSING LOGIC ---
        # Find the start of each section using the headers
        advice_start_index = raw_text.find('<advice>')
        portfolio_start_index = raw_text.find('<portfolio>')

        if advice_start_index == -1 or portfolio_start_index == -1:
            raise ValueError("AI response did not contain the required <advice> and <portfolio> markers.")

        # The advice text is the content between the two markers
        advice_text = raw_text[advice_start_index + len('<advice>'):portfolio_start_index].strip()
        
        # The portfolio block is all the content after its marker
        portfolio_block = raw_text[portfolio_start_index + len('<portfolio>'):].strip()
        # --- END OF NEW LOGIC ---

        json_match = re.search(r'\{.*\}', portfolio_block, re.DOTALL)
        if not json_match:
            raise ValueError("Could not find a valid JSON object within the portfolio section.")
        
        portfolio_json_str = json_match.group(0)

        # The rest of your parsing logic for recommendations and summary remains the same
        recommendations = [rec.strip() for rec in advice_text.split('\n') if re.match(r'^\s*[\*\-\d]', rec.strip())]

        summary_paragraph = advice_text
        if recommendations:
            # Try to find the first recommendation to separate it from the summary
            first_rec_index = advice_text.find(recommendations[0])
            if first_rec_index != -1:
                summary_paragraph = advice_text[:first_rec_index].strip()
        
        summary = {
            "monthly_savings_potential": f"₹{monthly_surplus:,.2f}",
            "your_investor_profile": risk_profile_description,
            "ai_summary": summary_paragraph
        }
        
        portfolio = json.loads(portfolio_json_str)
        
        return {"summary": summary, "recommendations": recommendations, "portfolio": portfolio}

    except Exception as e:
        print(f"An error occurred during recommendation generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate or parse AI-powered recommendations.")
    
@app.post("/api/plans")
def save_financial_plan(
    plan_data: RecommendationResponse,
    profile_data: UserFinancialProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Securely gets the logged-in user
):
    """Saves a generated financial plan to the current user's profile."""
    new_plan = FinancialPlan(
        # Save the user's inputs
        income=profile_data.income,
        expenses=profile_data.expenses,
        savings=profile_data.savings,
        risk_tolerance=profile_data.risk_tolerance_input,
        
        # Save the AI's outputs
        ai_summary=plan_data.summary.get("ai_summary"),
        recommendations_json=json.dumps(plan_data.recommendations),
        portfolio_json=json.dumps(plan_data.portfolio),
        
        # Link the plan to the logged-in user
        owner_id=current_user.id
    )
    
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    return {"message": "Financial plan saved successfully!", "plan_id": new_plan.id}

@app.get("/api/plans/me", response_model=List[PlanResponse])
def get_user_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Securely gets the logged-in user
):
    """Fetches all financial plans saved by the current logged-in user."""
    # This fetches plans and sorts them with the newest first
    return db.query(FinancialPlan).filter(FinancialPlan.owner_id == current_user.id).order_by(FinancialPlan.created_at.desc()).all()

@app.post("/api/health-score", response_model=HealthScoreResponse)
def get_health_score(profile: UserFinancialProfile):
    """Calculates a financial health score based on user inputs."""
    
    # 1. Calculate Savings Rate (most important metric)
    # The percentage of income saved each month.
    savings_rate = 0
    if profile.income > 0:
        savings_rate = ((profile.income - profile.expenses) / profile.income) * 100
    
    # 2. Calculate Savings Buffer (cushion for emergencies)
    # How many months of expenses are covered by savings.
    savings_buffer = 0
    if profile.expenses > 0:
        savings_buffer = profile.savings / profile.expenses
        
    # 3. Simple scoring logic (you can make this more complex)
    score = 0
    # 60 points from savings rate (e.g., 50% rate = 30 points)
    score += max(0, min(60, savings_rate * 1.2))
    # 40 points from savings buffer (e.g., 6 months buffer = 40 points)
    score += max(0, min(40, (savings_buffer / 6) * 40))
    
    score = int(score) # Convert to a whole number
    
    # 4. Provide a rating and feedback
    rating = "Needs Improvement"
    feedback = "Focus on increasing your monthly savings."
    if score > 80:
        rating = "Excellent"
        feedback = "You have outstanding financial discipline!"
    elif score > 60:
        rating = "Good"
        feedback = "You are on the right track. Keep it up!"
        
    return {"score": score, "rating": rating, "feedback": feedback}
