# backend/app.py

import os
import sys
from datetime import timedelta, datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import google.generativeai as genai
import json
import re
import requests
from dotenv import load_dotenv

# --- 1. Fix Import Paths ---
# This allows Python to find your 'backend' and 'ml' folders
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# --- 2. Import Custom Modules ---
from backend.database import get_db, create_database, User, FinancialPlan
from ml.fuzzy_logic import calculate_risk_profile
from backend.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# --- 3. API Key & Environment Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

# Safety check: Ensure all keys are present
if not all([GEMINI_API_KEY, NEWS_API_KEY, ALPHA_VANTAGE_KEY, SECRET_KEY]):
    # We print a warning instead of crashing, to allow local debugging if needed
    print("WARNING: One or more API keys are missing from your .env file.")

# Configure Gemini AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')

# AI Persona Instructions
SYSTEM_INSTRUCTION = """
You are 'IntellectMoney AI', a sophisticated financial analyst for Indian investors.
Your goal is to provide precise, high-level, and actionable financial information.

GUIDELINES:
1. **Be Direct:** Start immediately with the answer. Avoid filler phrases like "That is an excellent question" or "I am pleased to help."
2. **Be Concise:** Explain complex concepts in the fewest words possible without losing meaning.
3. **Structure:** Use Bullet points and Bold text (**text**) to make data scannable. Avoid long paragraphs.
4. **Tone:** Formal, objective, and professional (like a Bloomberg terminal or a Senior Wealth Manager).
5. **Context:** When explaining terms (like Mutual Funds, SIPs), focus on the definition, the mechanism, and the specific advantage for an Indian investor.
6. **No Emojis:** Do not use emojis unless absolutely necessary for clarity. Keep it clean.

Example Response Style:
"A **Mutual Fund** is a professional investment vehicle that pools capital from multiple investors to purchase securities.
* **Mechanism:** Money is managed by an Asset Management Company (AMC).
* **Benefit:** Provides diversification and professional management at a low cost.
* **Liquidity:** Open-ended funds offer high liquidity."
"""

# --- 4. App Setup ---
create_database() # Create tables if they don't exist
app = FastAPI(title="IntellectMoney API")

# CORS Middleware (Crucial for Frontend-Backend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend Files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# --- 5. Pydantic Models (Data Structures) ---

class UserCreate(BaseModel):
    fullname: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserFinancialProfile(BaseModel):
    income: float
    expenses: float
    savings: float
    financial_goal: Optional[str] = "General Wealth Building"
    risk_tolerance_input: str

class Alert(BaseModel):
    type: str
    icon: str
    message: str

class RecommendationResponse(BaseModel):
    summary: dict
    recommendations: List[str]
    portfolio: dict
    alerts: List[Alert] = []

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

class NewsArticle(BaseModel):
    title: str
    url: str
    summary: str
    source: str

class MarketNewsResponse(BaseModel):
    articles: List[NewsArticle]

class PlanResponse(BaseModel):
    id: int
    created_at: datetime
    income: float
    expenses: float
    ai_summary: str
    recommendations_json: str
    portfolio_json: str
    class Config:
        from_attributes = True

class HealthScoreResponse(BaseModel):
    score: int
    rating: str
    feedback: str


# --- 6. Helper Functions ---

def fetch_stock_price(symbol: str):
    """Fetches live stock price from Alpha Vantage."""
    api_symbol = symbol.split('.')[0] # Remove .NSE/.BSE suffix
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={api_symbol}&apikey={ALPHA_VANTAGE_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # Check for API errors or limits
        if "Note" in data:
            return "Sorry, the stock market API limit has been reached. Please try again tomorrow."
        
        quote = data.get("Global Quote")
        if not quote or not quote.get("05. price"):
            return f"Sorry, I found the symbol **{symbol}**, but I couldn't retrieve its price data right now."
        
        price = f"₹{float(quote['05. price']):.2f}"
        change_percent_str = quote.get('10. change percent', '0%')
        change_percent = float(change_percent_str.replace('%', ''))
        change_symbol = '▲' if change_percent >= 0 else '▼'
        
        return f"The current price of **{symbol}** is **{price}** ({change_symbol} {change_percent:.2f}%)."
    except Exception as e:
        print(f"Alpha Vantage API error: {e}")
        return "Sorry, I'm having trouble connecting to the stock market data service."

def check_financial_health_triggers(income: float, expenses: float, total_savings: float):
    """
    Acts as an autonomous agent that monitors financial health.
    """
    alerts = []
    
    # Calculate Monthly Savings (Cash Flow)
    monthly_savings = income - expenses
    savings_rate = (monthly_savings / income) * 100 if income > 0 else 0

    # Calculate Emergency Fund Coverage (Months of expenses covered)
    emergency_months = total_savings / expenses if expenses > 0 else 0
    
    # --- RULE 1: HIGH SPENDING (Habit Alert) ---
    if income > 0 and expenses > (income * 0.8):
        alerts.append({
            "type": "danger",
            "icon": "⚠️",
            "message": f"Critical: You are spending {int((expenses/income)*100)}% of your income. Immediate budgeting required."
        })
    
    # --- RULE 2: DEFICIT (Habit Alert) ---
    if expenses > income:
        alerts.append({
            "type": "danger",
            "icon": "🚨",
            "message": "Deficit Alert: You are spending more than you earn. You are burning through cash."
        })

    # --- RULE 3: LOW EMERGENCY FUND (Safety Alert) ---
    # If you have less than 3 months of expenses saved up
    if emergency_months < 3:
        alerts.append({
            "type": "warning",
            "icon": "📉",
            "message": f"Risk Detected: Your emergency fund only covers {emergency_months:.1f} months of expenses. Aim for 6 months."
        })

    # --- RULE 4: EXCELLENT HABITS (Habit Alert) ---
    # Real Monthly Savings Rate > 30%
    if savings_rate > 30:
        alerts.append({
            "type": "success",
            "icon": "🌟",
            "message": f"Excellent: You are saving {int(savings_rate)}% of your monthly income. You are on track for wealth building."
        })

    return alerts


# --- 7. API Endpoints ---

# --- User Authentication ---
@app.post("/api/register", response_model=Token)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check password length for bcrypt
    if len(user.password) > 72:
         raise HTTPException(status_code=400, detail="Password must be less than 72 characters")

    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password, fullname=user.fullname)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Auto-login after registration
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- Intelligent Chatbot ---
@app.post("/api/chatbot", response_model=ChatResponse)
def handle_chat(message: ChatMessage):
    user_message = message.message.strip()

    # 1. Intent Detection
    intent_prompt = f"""
        Analyze the user's question: "{user_message}"
        Is the user asking for a stock price?
        - If YES, respond with ONLY the most relevant Indian stock market ticker symbol (e.g., RELIANCE.NSE, TATAMOTORS.BSE).
        - If NO, respond with ONLY the word "GENERAL".
        Do not add any other text.
    """
    
    try:
        intent_response = model.generate_content(intent_prompt)
        classification = intent_response.text.strip()
        
        print(f"--- Chatbot Intent: {classification} ---")

        # 2. Stock Price Logic
        if "." in classification and "GENERAL" not in classification:
            stock_symbol = classification
            price_info = fetch_stock_price(stock_symbol)
            return {"reply": price_info}

        # 3. General Conversation Logic
        else:
            general_prompt = f"{SYSTEM_INSTRUCTION}\n\nUSER QUESTION: {user_message}"
            general_response = model.generate_content(general_prompt)
            return {"reply": general_response.text}

    except Exception as e:
        print(f"Chatbot Error: {e}")
        return {"reply": "I'm sorry, I'm having trouble connecting to my AI brain right now. Please try again."}


# --- Market News ---
@app.get("/api/market-news", response_model=MarketNewsResponse)
def get_market_news():
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q=finance&language=en&sortBy=publishedAt&pageSize=5"
        f"&apiKey={NEWS_API_KEY}"
    )
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("status") != "ok":
            raise HTTPException(status_code=500, detail="Failed to fetch news.")

        articles = [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "summary": a.get("description", "No summary available."),
                "source": a.get("source", {}).get("name", "Unknown"),
            }
            for a in data.get("articles", [])
        ]
        return {"articles": articles}
        
    except Exception as e:
        print(f"News API Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market news.")


# --- Core Feature: AI Financial Plan Generator ---
@app.post("/api/recommendations", response_model=RecommendationResponse)

@app.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(profile: UserFinancialProfile):
    # 1. Fuzzy Logic Risk Assessment
    risk_mapping = {"low": 3, "medium": 5, "high": 8}
    
    # Handle capitalization issues
    user_input_clean = profile.risk_tolerance_input.lower().strip()
    user_risk_preference = risk_mapping.get(user_input_clean, 5)
    
    calculated_risk_score = calculate_risk_profile(
        income=profile.income, 
        savings=profile.savings, 
        user_preference=user_risk_preference
    )
    
    print(f"DEBUG: Input={user_input_clean}, Score={calculated_risk_score:.2f}")

    # --- ADJUSTED THRESHOLDS ---
    if calculated_risk_score <= 3.5: 
        risk_profile_description = "Conservative Investor"
    elif calculated_risk_score <= 6.5: 
        risk_profile_description = "Balanced Investor"
    else: 
        risk_profile_description = "Growth-Oriented Investor"
    
    monthly_surplus = profile.income - profile.expenses

    # 2. Agentic Analysis (Watchdog)
    # Ensure you are using the version of this function that calculates (Income - Expenses)
    agent_alerts = check_financial_health_triggers(profile.income, profile.expenses, profile.savings)
    
    # Create context string for the AI
    agent_context_str = "\n".join([f"- {alert['message']}" for alert in agent_alerts])
    if not agent_context_str:
        agent_context_str = "- No critical risks detected. Standard planning applies."

    # 3. Generative AI Prompt with FINANCIAL GOAL
    prompt = f"""
    You are an expert financial advisor for an Indian user.
    
    >>> INTERNAL AGENT ANALYSIS (CRITICAL):
    The system's autonomous agent has already analyzed the user's health and found:
    {agent_context_str}
    
    >>> USER'S SPECIFIC GOAL:
    "{profile.financial_goal}"
    
    >>> INSTRUCTION FOR PORTFOLIO:
    Your portfolio allocation MUST align with the Agent Analysis above.
    - If "Excellent" or "High Savings", suggest an aggressive portfolio.
    - If "Critical" or "Deficit", focus heavily on Liquid Funds.
    
    >>> INSTRUCTION FOR GOAL:
    - SPECIFICALLY address how the user can achieve their goal ("{profile.financial_goal}") based on their monthly surplus of ₹{monthly_surplus:,.2f}.
    - Estimate the time in months/years it will take to save this amount.

    >>> USER PROFILE:
    <income>₹{profile.income:,.2f}</income>
    <expenses>₹{profile.expenses:,.2f}</expenses>
    <savings>₹{profile.savings:,.2f}</savings>
    <monthly_surplus>₹{monthly_surplus:,.2f}</monthly_surplus>
    <risk_tolerance>{profile.risk_tolerance_input}</risk_tolerance>
    <investor_type>{risk_profile_description}</investor_type>

    Your response MUST be in two distinct parts, marked with <advice> and <portfolio> headers.

    First, provide personalized advice under an <advice> header. This should include a summary paragraph and a bulleted or numbered list of 3-4 actionable recommendations.
    
    Second, provide a portfolio allocation under a <portfolio> header. This MUST be a single, valid JSON object with "labels" and "data" keys. The data values must sum to 100.
    """

    try:
        response = model.generate_content(prompt)
        raw_text = response.text
        print("--- AI Raw Response --- \n", raw_text, "\n-----------------------")
        
        # 4. Robust Parsing Logic
        advice_start_index = raw_text.find('<advice>')
        portfolio_start_index = raw_text.find('<portfolio>')

        if advice_start_index == -1 or portfolio_start_index == -1:
            raise ValueError("AI response format error: missing tags.")

        advice_text = raw_text[advice_start_index + len('<advice>'):portfolio_start_index].strip()
        portfolio_block = raw_text[portfolio_start_index + len('<portfolio>'):].strip()

        json_match = re.search(r'\{.*\}', portfolio_block, re.DOTALL)
        if not json_match:
            raise ValueError("Could not find JSON in portfolio block.")
        
        portfolio_json_str = json_match.group(0)
        portfolio = json.loads(portfolio_json_str)

        recommendations = [
            rec.strip() 
            for rec in advice_text.split('\n') 
            if re.match(r'^\s*[\*\-\d]', rec.strip())
        ]

        summary_paragraph = advice_text
        if recommendations:
            first_rec_index = advice_text.find(recommendations[0])
            if first_rec_index != -1:
                summary_paragraph = advice_text[:first_rec_index].strip()
        
        summary = {
            "monthly_savings_potential": f"₹{monthly_surplus:,.2f}",
            "your_investor_profile": risk_profile_description,
            "ai_summary": summary_paragraph
        }
        
        return {
            "summary": summary, 
            "recommendations": recommendations, 
            "portfolio": portfolio,
            "alerts": agent_alerts 
        }

    except Exception as e:
        print(f"Recommendation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations.")

# --- Saving Plans ---
@app.post("/api/plans")
def save_financial_plan(
    plan_data: RecommendationResponse,
    profile_data: UserFinancialProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_plan = FinancialPlan(
        income=profile_data.income,
        expenses=profile_data.expenses,
        savings=profile_data.savings,
        risk_tolerance=profile_data.risk_tolerance_input,
        ai_summary=plan_data.summary.get("ai_summary"),
        recommendations_json=json.dumps(plan_data.recommendations),
        portfolio_json=json.dumps(plan_data.portfolio),
        owner_id=current_user.id
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return {"message": "Financial plan saved successfully!", "plan_id": new_plan.id}

# --- Retrieving Plans ---
@app.get("/api/plans/me", response_model=List[PlanResponse])
def get_user_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(FinancialPlan).filter(FinancialPlan.owner_id == current_user.id).order_by(FinancialPlan.created_at.desc()).all()

# --- Health Score ---
@app.post("/api/health-score", response_model=HealthScoreResponse)
def get_health_score(profile: UserFinancialProfile):
    # 1. Calculate Metrics
    savings_rate = 0
    if profile.income > 0:
        savings_rate = ((profile.income - profile.expenses) / profile.income) * 100
    
    savings_buffer = 0
    if profile.expenses > 0:
        savings_buffer = profile.savings / profile.expenses
        
    # 2. Scoring Logic
    score = 0
    score += max(0, min(60, savings_rate * 1.2)) # Max 60 pts from rate
    score += max(0, min(40, (savings_buffer / 6) * 40)) # Max 40 pts from buffer
    
    score = int(score)
    
    # 3. Rating
    rating = "Needs Improvement"
    feedback = "Focus on increasing your monthly savings."
    if score > 80:
        rating = "Excellent"
        feedback = "You have outstanding financial discipline!"
    elif score > 60:
        rating = "Good"
        feedback = "You are on the right track. Keep it up!"
        
    return {"score": score, "rating": rating, "feedback": feedback}