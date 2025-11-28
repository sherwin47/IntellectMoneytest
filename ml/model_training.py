# ml/model_training.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
import joblib 
import os


print("Step 1: Loading data...")

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'historical_prices.csv')
df = pd.read_csv(DATA_PATH)
df['Date'] = pd.to_datetime(df['Date'])
df.sort_values('Date', inplace=True)
df.set_index('Date', inplace=True)

print("Data loaded successfully.")
print(df.head())


print("\nStep 2: Engineering features...")


df['SMA_5'] = df['Close'].rolling(window=5).mean() 
df['SMA_20'] = df['Close'].rolling(window=20).mean() 


delta = df['Close'].diff()

gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))


df.dropna(inplace=True)
print("Features created:")
print(df.head())



print("\nStep 3: Defining the prediction target...")

prediction_horizon = 5
df['target'] = df['Close'].shift(-prediction_horizon)


df.dropna(inplace=True)
print(f"Target variable ('target') is the closing price {prediction_horizon} days ahead.")
print(df[['Close', 'target']].head())



print("\nStep 4: Preparing data for model training...")

features = ['Open', 'High', 'Low', 'Close', 'Volume', 'SMA_5', 'SMA_20', 'RSI']
X = df[features]
y = df['target']


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

print(f"Training set size: {len(X_train)} samples")
print(f"Testing set size: {len(X_test)} samples")



print("\nStep 5: Training the Gradient Boosting Regressor model...")
model = GradientBoostingRegressor(
    n_estimators=100,    
    learning_rate=0.1,    
    max_depth=3,          
    random_state=42       
)


model.fit(X_train, y_train)
print("Model training complete.")



print("\nStep 6: Evaluating the model...")

predictions = model.predict(X_test)


mse = mean_squared_error(y_test, predictions)
print(f"Model Performance (Mean Squared Error): {mse:.4f}")


results = pd.DataFrame({'Actual': y_test, 'Predicted': predictions})
print("Sample predictions:")
print(results.head())



print("\nStep 7: Saving the trained model...")
MODEL_SAVE_PATH = os.path.join(os.path.dirname(__file__), 'investment_model.pkl')
joblib.dump(model, MODEL_SAVE_PATH)
print(f"Model saved successfully to: {MODEL_SAVE_PATH}")
print("\nThis file can now be loaded by the backend (app.py) to make live predictions.")