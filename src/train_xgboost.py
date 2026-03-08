import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import os
import json

def generate_synthetic_data(num_samples=1000):
    """
    Generates dummy trading data for pipeline demonstration.
    Features: RSI, MACD_Hist, Dist_to_EMA, Vol_Relative, MSS_Signal, Sweep_Signal
    Target: 1 (Win), 0 (Loss)
    """
    np.random.seed(42)
    
    # RSI: 0-100
    rsi = np.random.uniform(20, 80, num_samples)
    # MACD Histogram
    macd_hist = np.random.normal(0, 5, num_samples)
    # Distance to EMA (normalized)
    dist_ema = np.random.normal(0, 10, num_samples)
    # Volume relative to SMA
    vol_rel = np.random.uniform(0.5, 3.0, num_samples)
    # Binary signals
    mss = np.random.choice([0, 1], num_samples)
    sweep = np.random.choice([0, 1], num_samples)
    
    # Simple logic for synthetic target: 
    # Win if (RSI < 30 and MACD > 0) or (MSS and Sweep and vol_rel > 1.5)
    # Adding some noise
    prob = (
        0.3 * (rsi < 35) + 
        0.2 * (macd_hist > 1) + 
        0.4 * (mss & sweep) + 
        0.1 * (vol_rel > 1.8)
    )
    # Normalize prob to 0-1 and add noise
    prob = np.clip(prob + np.random.normal(0, 0.1, num_samples), 0, 1)
    target = (prob > 0.5).astype(int)
    
    df = pd.DataFrame({
        'rsi': rsi,
        'macd_hist': macd_hist,
        'dist_ema': dist_ema,
        'vol_rel': vol_rel,
        'mss': mss,
        'sweep': sweep,
        'target': target
    })
    return df

def train_xgb():
    # 1. Load Data
    data_path = "data/training_signals.csv"
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        print(f"Loaded {len(df)} samples from {data_path}")
    else:
        print("Real data not found. Generating synthetic data for pipeline verification...")
        df = generate_synthetic_data()
    
    X = df.drop(columns=['target'])
    y = df['target']
    
    # 2. Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 3. Model Parameters
    # Optimized for binary classification
    params = {
        'objective': 'binary:logistic',
        'max_depth': 4,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'eval_metric': 'logloss'
    }
    
    model = xgb.XGBClassifier(**params)
    
    # 4. Train
    model.fit(X_train, y_train)
    
    # 5. Evaluate
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"XGBoost Test Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, preds))
    
    # 6. Save Model
    os.makedirs("data", exist_ok=True)
    model_path = "data/signal_xgb_model.json"
    model.save_model(model_path)
    
    # Save feature names for inference alignment
    with open("data/xgb_features.json", "w") as f:
        json.dump(list(X.columns), f)
        
    print(f"XGBoost model saved to {model_path}")

if __name__ == "__main__":
    train_xgb()
