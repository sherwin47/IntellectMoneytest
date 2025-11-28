import pandas as pd



def preprocess_market_data(file_path: str):
    """
    Loads and preprocesses market data, creating new features.
    """
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df.dropna(inplace=True)
    
    return df

