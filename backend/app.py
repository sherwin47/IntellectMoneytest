# backend/app.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
import re
import requests

# Import our custom modules
from backend.database import (
    get_db, create_database,
    User, get_password_hash, verify_password
)
from ml.fuzzy_logic import calculate_risk_profile

# --- API Key Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY") # Use the new NewsAPI key

if not GEMINI_API_KEY or not NEWS_API_KEY:
    raise ValueError("An API key is missing. Make sure GEMINI_API_KEY and NEWS_API_KEY are in your .env file.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')
SYSTEM_INSTRUCTION = (
    "You are an expert financial assistant for 'IntellectMoney', a service for an Indian user. "
    "Your tone must be professional, clear, and encouraging. "
    # ... (rest of instructions)
)
# ---

# Create the database tables
create_database()

app = FastAPI(title="IntellectMoney API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Pydantic Models ---
class UserCreate(BaseModel): fullname: str; email: str; password: str
class UserLogin(BaseModel): email: str; password: str
class UserFinancialProfile(BaseModel): income: float; expenses: float; savings: float; risk_tolerance_input: str
class RecommendationResponse(BaseModel): summary: dict; recommendations: List[str]; portfolio: dict
class ChatMessage(BaseModel): message: str
class ChatResponse(BaseModel): reply: str

class NewsArticle(BaseModel):
    title: str
    url: str
    summary: str
    source: str

class MarketNewsResponse(BaseModel):
    articles: List[NewsArticle]

# --- API Endpoints ---

@app.post("/api/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user: raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password, fullname=user.fullname)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"message": "User registered successfully"}

@app.post("/api/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"message": "Login successful"}

@app.post("/api/chatbot", response_model=ChatResponse)
def handle_chat(message: ChatMessage):
    user_message = message.message.strip()
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\nUSER QUESTION: {user_message}"
    try:
        response = model.generate_content(full_prompt)
        return {"reply": response.text}
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Failed to get a response from the AI model.")

# --- UPGRADED Market News Endpoint (Using NewsAPI.org) ---
@app.get("/api/market-news", response_model=MarketNewsResponse)
def get_market_news():
    """Fetches the latest financial market news from NewsAPI.org."""
    # UPDATED: Search for a broader keyword 'finance' instead of a specific category
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q=finance&language=en&sortBy=publishedAt&pageSize=5"
        f"&apiKey={NEWS_API_KEY}"
    )
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("status") != "ok":
            raise HTTPException(status_code=500, detail="Failed to fetch news from NewsAPI.")

        articles_data = data.get("articles", [])
        
        articles = [
            {
                "title": article.get("title"),
                "url": article.get("url"),
                "summary": article.get("description", "No summary available."), # NewsAPI uses 'description'
                "source": article.get("source", {}).get("name", "Unknown"),
            }
            for article in articles_data
        ]
        return {"articles": articles}
        
    except Exception as e:
        print(f"An error occurred while fetching news: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market news.")


@app.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(profile: UserFinancialProfile):
    """
    Generates unique, AI-powered financial recommendations using Gemini.
    """
    # ... (The rest of your recommendations function remains the same)
    risk_mapping = {"low": 3, "medium": 5, "high": 8}
    user_risk_preference = risk_mapping.get(profile.risk_tolerance_input, 5)
    calculated_risk_score = calculate_risk_profile(
        income=profile.income, savings=profile.savings, user_preference=user_risk_preference
    )
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

    Your response MUST be in two distinct parts.

    First, provide personalized advice inside <advice> tags. This should include a summary paragraph and a bulleted or numbered list of 3-4 actionable recommendations.
    
    Second, provide a portfolio allocation inside <portfolio> tags. This MUST be a single, valid JSON object with "labels" and "data" keys. The data values must sum to 100.
    """

    try:
        response = model.generate_content(prompt)
        print("--- AI Raw Response --- \n", response.text, "\n-----------------------")
        
        advice_match = re.search(r'<(?:advice|summary)>(.*?)</(?:advice|summary)>', response.text, re.DOTALL)
        portfolio_match = re.search(r'<portfolio>(.*?)</portfolio>', response.text, re.DOTALL)

        if not advice_match or not portfolio_match:
            raise ValueError("AI response did not contain the required advice and portfolio tags.")
            
        advice_text = advice_match.group(1).strip()
        portfolio_block = portfolio_match.group(1).strip()

        json_match = re.search(r'\{.*\}', portfolio_block, re.DOTALL)
        if not json_match:
            raise ValueError("Could not find a valid JSON object within the <portfolio> tags.")
        
        portfolio_json_str = json_match.group(0)

        recommendations = []
        list_items = re.findall(r'<(?:item|li)>(.*?)</(?:item|li)>', advice_text, re.DOTALL)
        if list_items:
            recommendations = [item.strip() for item in list_items]
        else:
            recommendations = [rec.strip() for rec in advice_text.split('\n') if re.match(r'^\s*[\*\-\d]', rec.strip())]

        first_rec_index = advice_text.find(recommendations[0]) if recommendations else -1
        summary_paragraph = advice_text[:first_rec_index].strip() if first_rec_index != -1 else advice_text
        
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