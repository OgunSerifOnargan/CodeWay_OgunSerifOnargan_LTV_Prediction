import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import pickle
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def save_test_results_to_db():
    """Save test predictions to database for evaluation"""
    
    print("🚀 SAVING TEST RESULTS TO DATABASE...")
    print("="*60)
    
    engine = create_engine(DB_URL)
    
    # Load test dataset
    print("📥 Loading test dataset...")
    test_df = pd.read_csv('../data/test_dataset.csv')
    print(f"   ✅ Loaded {len(test_df):,} test samples")
    
    # Load best model
    print("🤖 Loading best model (LightGBM)...")
    with open('../models/lightgbm_model.pkl', 'rb') as f:
        model_data = pickle.load(f)
        model = model_data['model']
    print("   ✅ Model loaded successfully")
    
    # Load feature info
    with open('../data/feature_info.json', 'r') as f:
        feature_info = json.load(f)
    
    # Prepare features
    print("🔧 Preparing features for prediction...")
    feature_columns = feature_info['model_features']
    X_test = test_df[feature_columns]
    
    # Generate predictions
    print("🎯 Generating predictions...")
    predictions = model.predict(X_test)
    
    # Prepare results dataframe
    print("📊 Preparing results...")
    results_df = pd.DataFrame({
        'user_id': test_df['user_id'],
        'country': test_df['country'], 
        'first_event_date': test_df['first_event_date'],
        'actual_ltv': test_df['first_year_revenue'],
        'predicted_ltv': predictions,
        'prediction_date': datetime.now(),
        'model_type': 'LightGBM'
    })
    
    # Calculate additional metrics
    results_df['prediction_error'] = results_df['predicted_ltv'] - results_df['actual_ltv']
    results_df['absolute_error'] = np.abs(results_df['prediction_error'])
    results_df['is_paying_user'] = (results_df['actual_ltv'] > 0).astype(int)
    results_df['predicted_paying_user'] = (results_df['predicted_ltv'] > 0).astype(int)
    
    print(f"   ✅ Prepared {len(results_df):,} prediction results")
    
    # Save to database
    print("💾 Saving to database...")
    
    # Drop table if exists and create new one
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_predictions"))
        conn.commit()
    
    # Save results
    results_df.to_sql('test_predictions', engine, index=False, if_exists='replace', 
                     method='multi', chunksize=10000)
    
    print(f"   ✅ Saved {len(results_df):,} records to 'test_predictions' table")
    
    # Print summary statistics
    print("\n📈 PREDICTION SUMMARY:")
    print("="*40)
    print(f"Total Users: {len(results_df):,}")
    print(f"Actual Total LTV: ${results_df['actual_ltv'].sum():,.2f}")
    print(f"Predicted Total LTV: ${results_df['predicted_ltv'].sum():,.2f}")
    print(f"Revenue Accuracy: {(results_df['predicted_ltv'].sum() / results_df['actual_ltv'].sum() * 100):.1f}%")
    print(f"Mean Absolute Error: ${results_df['absolute_error'].mean():.2f}")
    print(f"RMSE: ${np.sqrt(results_df['prediction_error']**2).mean():.2f}")
    
    # Paying users analysis
    actual_paying = results_df['is_paying_user'].sum()
    predicted_paying = results_df['predicted_paying_user'].sum()
    print(f"\nActual Paying Users: {actual_paying:,} ({actual_paying/len(results_df)*100:.1f}%)")
    print(f"Predicted Paying Users: {predicted_paying:,} ({predicted_paying/len(results_df)*100:.1f}%)")
    
    print("\n🎉 TEST RESULTS SAVED TO DATABASE!")
    return results_df

if __name__ == "__main__":
    results = save_test_results_to_db()
