import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

class LTVPredictor:
    """LTV Prediction Pipeline using the best trained model"""
    
    def __init__(self, model_path='../models/lightgbm_model.pkl', feature_info_path='../data/feature_info.json'):
        """Initialize the LTV predictor with trained model and feature info"""
        
        print("🔄 INITIALIZING LTV PREDICTOR...")
        
        # Load the best model
        with open(model_path, 'rb') as f:
            self.model_data = pickle.load(f)
        
        self.model = self.model_data['model']
        
        # Load feature information
        with open(feature_info_path, 'r') as f:
            self.feature_info = json.load(f)
        
        self.model_features = self.feature_info['model_features']
        self.label_encoders = self.feature_info['label_encoders']
        
        print(f"   ✅ Loaded LightGBM model")
        print(f"   ✅ Model features: {len(self.model_features)}")
        print(f"   ✅ Ready for predictions!")
    
    def prepare_user_features(self, user_ids):
        """Prepare features for given user IDs from database"""
        
        print(f"\n📥 PREPARING FEATURES FOR {len(user_ids):,} USERS...")
        
        engine = create_engine(DB_URL)
        
        # Create user ID list for SQL query (properly quote string IDs)
        user_id_str = ','.join([f"'{uid}'" for uid in user_ids])
        
        # Load target and basic info
        target_query = f"""
        SELECT 
            user_id,
            first_year_revenue,
            country,
            first_event_date
        FROM raw_dataset
        WHERE user_id IN ({user_id_str})
        GROUP BY user_id, first_year_revenue, country, first_event_date
        """
        
        user_data = pd.read_sql(target_query, engine)
        print(f"   ✅ Loaded basic info for {len(user_data):,} users")
        
        # Merge feature tables
        feature_tables = [
            'post_subscription_features',
            'pre_subscription_features', 
            'revenue_features',
            'rfm_features',
            'training_table'
        ]
        
        for table in feature_tables:
            try:
                table_query = f"SELECT * FROM {table} WHERE user_id IN ({user_id_str})"
                table_data = pd.read_sql(table_query, engine)
                
                before_count = len(user_data)
                user_data = user_data.merge(table_data, on='user_id', how='left')
                after_count = len(user_data)
                
                print(f"   ✅ Merged {table}: {before_count:,} → {after_count:,} users")
            except Exception as e:
                print(f"   ❌ Error with {table}: {str(e)}")
        
        return user_data
    
    def preprocess_features(self, user_data):
        """Preprocess features for model prediction"""
        
        print(f"\n🔧 PREPROCESSING FEATURES...")
        
        # Handle missing values
        processed_data = user_data.copy()
        
        # Fill missing numerical features with 0
        numerical_features = [f for f in self.feature_info['numerical_features'] if f in processed_data.columns]
        for feature in numerical_features:
            processed_data[feature] = processed_data[feature].fillna(0)
        
        # Fill missing categorical features with 'missing'
        categorical_features = [f for f in self.feature_info['categorical_features'] if f in processed_data.columns]
        for feature in categorical_features:
            processed_data[feature] = processed_data[feature].fillna('missing')
        
        # Encode categorical variables
        for feature in categorical_features:
            if feature in processed_data.columns:
                # Get the encoder classes
                encoder_classes = self.label_encoders.get(feature, [])
                
                # Create mapping
                class_to_index = {cls: idx for idx, cls in enumerate(encoder_classes)}
                
                # Encode values, unknown categories get mapped to 0 (first class)
                processed_data[f'{feature}_encoded'] = processed_data[feature].map(
                    lambda x: class_to_index.get(str(x), 0)
                )
        
        # Select model features
        encoded_categorical = [f'{f}_encoded' for f in categorical_features if f in processed_data.columns]
        all_model_features = numerical_features + encoded_categorical
        
        # Ensure all required features are present
        missing_features = set(self.model_features) - set(all_model_features)
        if missing_features:
            print(f"   ⚠️ Missing features: {missing_features}")
            # Add missing features with default values
            for feature in missing_features:
                processed_data[feature] = 0
        
        # Create feature matrix
        X = processed_data[self.model_features]
        
        print(f"   ✅ Feature matrix: {X.shape}")
        print(f"   ✅ Missing values handled")
        print(f"   ✅ Categorical variables encoded")
        
        return X, processed_data
    
    def predict_ltv(self, user_ids):
        """Predict LTV for given user IDs"""
        
        print(f"\n🎯 PREDICTING LTV FOR {len(user_ids):,} USERS...")
        print("="*60)
        
        # Prepare features
        user_data = self.prepare_user_features(user_ids)
        X, processed_data = self.preprocess_features(user_data)
        
        # Make predictions
        print(f"\n🚀 GENERATING PREDICTIONS...")
        predictions = self.model.predict(X)
        
        # Ensure non-negative predictions
        predictions = np.maximum(predictions, 0)
        
        # Create results DataFrame
        results = pd.DataFrame({
            'user_id': processed_data['user_id'],
            'country': processed_data['country'],
            'first_event_date': processed_data['first_event_date'],
            'predicted_ltv': predictions
        })
        
        # Add actual LTV if available (for validation)
        if 'first_year_revenue' in processed_data.columns:
            results['actual_ltv'] = processed_data['first_year_revenue']
            results['prediction_error'] = abs(results['predicted_ltv'] - results['actual_ltv'])
        
        print(f"   ✅ Generated {len(results):,} predictions")
        
        return results
    
    def predict_sample_users(self, n_users=1000):
        """Predict LTV for a random sample of users"""
        
        print(f"\n🎲 PREDICTING LTV FOR RANDOM SAMPLE OF {n_users:,} USERS...")
        
        engine = create_engine(DB_URL)
        
        # Get random sample of user IDs
        sample_query = f"""
        SELECT user_id 
        FROM raw_dataset 
        ORDER BY RANDOM() 
        LIMIT {n_users}
        """
        
        sample_users = pd.read_sql(sample_query, engine)
        user_ids = sample_users['user_id'].tolist()
        
        # Make predictions
        results = self.predict_ltv(user_ids)
        
        return results
    
    def analyze_predictions(self, results):
        """Analyze and summarize predictions"""
        
        print(f"\n📊 PREDICTION ANALYSIS:")
        print("="*60)
        
        # Basic statistics
        print(f"📈 PREDICTION STATISTICS:")
        print(f"   Users: {len(results):,}")
        print(f"   Mean Predicted LTV: ${results['predicted_ltv'].mean():.2f}")
        print(f"   Median Predicted LTV: ${results['predicted_ltv'].median():.2f}")
        print(f"   Std Predicted LTV: ${results['predicted_ltv'].std():.2f}")
        print(f"   Min Predicted LTV: ${results['predicted_ltv'].min():.2f}")
        print(f"   Max Predicted LTV: ${results['predicted_ltv'].max():.2f}")
        print(f"   Total Predicted Revenue: ${results['predicted_ltv'].sum():,.2f}")
        
        # Predicted paying users
        predicted_paying = (results['predicted_ltv'] > 0).sum()
        print(f"   Predicted Paying Users: {predicted_paying:,} ({predicted_paying/len(results)*100:.2f}%)")
        
        # If actual LTV is available, show comparison
        if 'actual_ltv' in results.columns:
            print(f"\n🎯 ACCURACY ANALYSIS:")
            actual_total = results['actual_ltv'].sum()
            predicted_total = results['predicted_ltv'].sum()
            accuracy = (1 - abs(actual_total - predicted_total) / actual_total) * 100
            
            print(f"   Actual Total LTV: ${actual_total:,.2f}")
            print(f"   Predicted Total LTV: ${predicted_total:,.2f}")
            print(f"   Revenue Accuracy: {accuracy:.2f}%")
            print(f"   Mean Absolute Error: ${results['prediction_error'].mean():.2f}")
        
        # Top countries by predicted LTV
        print(f"\n🌍 TOP COUNTRIES BY PREDICTED LTV:")
        country_ltv = results.groupby('country')['predicted_ltv'].agg(['count', 'mean', 'sum']).round(2)
        country_ltv = country_ltv.sort_values('sum', ascending=False).head(10)
        
        for country, row in country_ltv.iterrows():
            print(f"   {country:<5}: {row['count']:>6,} users, avg ${row['mean']:>6.2f}, total ${row['sum']:>10,.2f}")
        
        return results

def main():
    """Main prediction pipeline"""
    
    print("🚀 STARTING LTV PREDICTION PIPELINE...")
    print("="*60)
    
    # Initialize predictor
    predictor = LTVPredictor()
    
    # Option 1: Predict for sample users
    sample_results = predictor.predict_sample_users(n_users=5000)
    
    # Analyze predictions
    analyzed_results = predictor.analyze_predictions(sample_results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"../results/ltv_predictions_{timestamp}.csv"
    
    # Save with required columns: user_id, country, first_event_date, predicted_ltv
    output_columns = ['user_id', 'country', 'first_event_date', 'predicted_ltv']
    if 'actual_ltv' in analyzed_results.columns:
        output_columns.append('actual_ltv')
    
    analyzed_results[output_columns].to_csv(output_file, index=False)
    
    print(f"\n💾 RESULTS SAVED:")
    print(f"   File: {output_file}")
    print(f"   Columns: {', '.join(output_columns)}")
    print(f"   Records: {len(analyzed_results):,}")
    
    print(f"\n🎉 LTV PREDICTION COMPLETED!")
    print("="*60)
    print(f"✅ Successfully predicted LTV for {len(analyzed_results):,} users")
    print(f"✅ Total predicted revenue: ${analyzed_results['predicted_ltv'].sum():,.2f}")
    print(f"✅ Results saved to: {output_file}")
    
    return analyzed_results, predictor

if __name__ == "__main__":
    results, predictor = main()
