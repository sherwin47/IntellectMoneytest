# ml/model_training.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
import joblib # Used for saving the trained model
import os

# --- 1. Data Loading and Preprocessing ---
print("Step 1: Loading data...")
# Construct the path to the data file relative to the current script
# This makes the script runnable from the project's root directory
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'historical_prices.csv')
df = pd.read_csv(DATA_PATH)
df['Date'] = pd.to_datetime(df['Date'])
df.sort_values('Date', inplace=True)
df.set_index('Date', inplace=True)

print("Data loaded successfully.")
print(df.head())

# --- 2. Feature Engineering ---
# As outlined in the presentation, we create meaningful features for the model.
print("\nStep 2: Engineering features...")

# Simple Moving Averages (SMA)
df['SMA_5'] = df['Close'].rolling(window=5).mean()  # 5-day average
df['SMA_20'] = df['Close'].rolling(window=20).mean() # 20-day average

# Momentum Indicator (Relative Strength Index - RSI)
# Calculate price differences
delta = df['Close'].diff()
# Get positive and negative gains
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
# Calculate RS and RSI
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# We drop rows with NaN values created by the rolling windows
df.dropna(inplace=True)
print("Features created:")
print(df.head())


# --- 3. Defining the Prediction Target (Label) ---
# The objective is to predict future prices.
print("\nStep 3: Defining the prediction target...")
# We want to predict the closing price 5 days in the future
prediction_horizon = 5
df['target'] = df['Close'].shift(-prediction_horizon)

# Drop the last 'n' rows where the target is NaN
df.dropna(inplace=True)
print(f"Target variable ('target') is the closing price {prediction_horizon} days ahead.")
print(df[['Close', 'target']].head())


# --- 4. Preparing Data for the Model ---
print("\nStep 4: Preparing data for model training...")
# Define our features (X) and target (y)
features = ['Open', 'High', 'Low', 'Close', 'Volume', 'SMA_5', 'SMA_20', 'RSI']
X = df[features]
y = df['target']

# Split the data into training and testing sets
# We use shuffle=False because this is time-series data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

print(f"Training set size: {len(X_train)} samples")
print(f"Testing set size: {len(X_test)} samples")


# --- 5. Model Training ---
# This is the core "Model Training" step from the presentation's next steps.
print("\nStep 5: Training the Gradient Boosting Regressor model...")
model = GradientBoostingRegressor(
    n_estimators=100,     # Number of boosting stages
    learning_rate=0.1,    # Controls the contribution of each tree
    max_depth=3,          # Limits the depth of individual trees
    random_state=42       # Ensures reproducibility
)

# Train the model on the training data
model.fit(X_train, y_train)
print("Model training complete.")


# --- 6. Model Evaluation ---
print("\nStep 6: Evaluating the model...")
# Make predictions on the test set
predictions = model.predict(X_test)

# Calculate the Mean Squared Error (a common metric for regression)
mse = mean_squared_error(y_test, predictions)
print(f"Model Performance (Mean Squared Error): {mse:.4f}")

# Display a few sample predictions vs actual values
results = pd.DataFrame({'Actual': y_test, 'Predicted': predictions})
print("Sample predictions:")
print(results.head())


# --- 7. Saving the Model ---
# This process is called serialization. It saves the trained model to a file.
print("\nStep 7: Saving the trained model...")
MODEL_SAVE_PATH = os.path.join(os.path.dirname(__file__), 'investment_model.pkl')
joblib.dump(model, MODEL_SAVE_PATH)
print(f"Model saved successfully to: {MODEL_SAVE_PATH}")
print("\nThis file can now be loaded by the backend (app.py) to make live predictions.")