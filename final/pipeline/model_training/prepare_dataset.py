import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import json
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def prepare_ltv_dataset():
    """Prepare the final dataset for LTV prediction model training"""
    
    print("🔄 PREPARING LTV PREDICTION DATASET...")
    print("="*60)
    
    engine = create_engine(DB_URL)
    
    # Load final feature selection
    with open('../../final_feature_selection.json', 'r') as f:
        feature_config = json.load(f)
    
    numerical_features = feature_config['numerical_features']['all']
    categorical_features = feature_config['categorical_features']
    
    print(f"📊 Selected Features:")
    print(f"   Numerical: {len(numerical_features)}")
    print(f"   Categorical: {len(categorical_features)}")
    print(f"   Total: {len(numerical_features) + len(categorical_features)}")
    
    # Step 1: Load target data
    print(f"\n📥 Loading target data from test_raw_dataset...")
    target_query = """
    SELECT 
        user_id,
        MAX(first_year_revenue) as first_year_revenue,
        MAX(country) as country,
        MAX(first_event_date) as first_event_date
    FROM test_raw_dataset
    GROUP BY user_id
    """
    
    target_data = pd.read_sql(target_query, engine)
    print(f"   ✅ Loaded {len(target_data):,} users")
    
    # Step 2: Load and merge feature tables
    print(f"\n🔗 Loading and merging feature tables...")
    
    feature_tables = [
        'test_post_subscription_features',
        'test_pre_subscription_features', 
        'test_revenue_features',
        'test_rfm_features',
        'training_table',
        'test_non_paying_user_features',
        'operating_system_features'
    ]
    
    master_data = target_data.copy()
    
    for table in feature_tables:
        try:
            table_data = pd.read_sql(f"SELECT * FROM {table}", engine)
            before_count = len(master_data)
            
            # Handle duplicate columns (keep only user_id for merge)
            if table == 'non_paying_user_features':
                # Drop duplicate columns that exist in master_data
                overlap_cols = set(table_data.columns) & set(master_data.columns)
                overlap_cols.discard('user_id')  # Keep user_id for merge
                if overlap_cols:
                    print(f"      Dropping duplicate columns: {list(overlap_cols)}")
                    table_data = table_data.drop(columns=list(overlap_cols))
            
            master_data = master_data.merge(table_data, on='user_id', how='left')
            after_count = len(master_data)
            print(f"   ✅ Merged {table}: {before_count:,} → {after_count:,} users")
        except Exception as e:
            print(f"   ❌ Error with {table}: {str(e)}")
    
    print(f"   ✅ Final merged dataset: {len(master_data):,} users, {len(master_data.columns)} columns")
    
    # Step 3: Select final features
    print(f"\n🎯 Selecting final features...")
    
    # Check feature availability
    available_numerical = []
    missing_numerical = []
    
    for feature in numerical_features:
        if feature in master_data.columns:
            available_numerical.append(feature)
        else:
            missing_numerical.append(feature)
    
    available_categorical = []
    missing_categorical = []
    
    for feature in categorical_features:
        if feature in master_data.columns:
            available_categorical.append(feature)
        else:
            missing_categorical.append(feature)
    
    print(f"   Available numerical: {len(available_numerical)}/{len(numerical_features)}")
    print(f"   Available categorical: {len(available_categorical)}/{len(categorical_features)}")
    
    if missing_numerical:
        print(f"   ❌ Missing numerical: {missing_numerical}")
    if missing_categorical:
        print(f"   ❌ Missing categorical: {missing_categorical}")
    
    # Create final dataset with selected features
    final_features = available_numerical + available_categorical + ['user_id', 'first_year_revenue', 'country', 'first_event_date']
    final_data = master_data[final_features].copy()
    
    print(f"   ✅ Final dataset shape: {final_data.shape}")
    
    # Step 4: Data cleaning and preprocessing
    print(f"\n🧹 Data cleaning and preprocessing...")
    
    # Handle missing values
    print(f"   Checking missing values...")
    missing_info = final_data.isnull().sum()
    missing_features = missing_info[missing_info > 0]
    
    if len(missing_features) > 0:
        print(f"   Missing values found:")
        for feature, count in missing_features.items():
            pct = (count / len(final_data)) * 100
            print(f"      {feature}: {count:,} ({pct:.2f}%)")
        
        # Fill missing values
        for feature in available_numerical:
            if feature in missing_features.index:
                final_data[feature] = final_data[feature].fillna(0)
                print(f"      ✅ Filled {feature} with 0")
        
        for feature in available_categorical:
            if feature in missing_features.index:
                final_data[feature] = final_data[feature].fillna('missing')
                print(f"      ✅ Filled {feature} with 'missing'")
    else:
        print(f"   ✅ No missing values found")
    
    # Step 5: Target variable analysis
    print(f"\n📈 Target variable analysis...")
    target = final_data['first_year_revenue']
    
    print(f"   Count: {len(target):,}")
    print(f"   Non-zero: {(target > 0).sum():,} ({(target > 0).mean()*100:.2f}%)")
    print(f"   Mean: ${target.mean():.2f}")
    print(f"   Median: ${target.median():.2f}")
    print(f"   Std: ${target.std():.2f}")
    print(f"   Min: ${target.min():.2f}")
    print(f"   Max: ${target.max():.2f}")
    
    # Step 6: Encode categorical variables
    print(f"\n🔢 Encoding categorical variables...")
    
    encoded_data = final_data.copy()
    label_encoders = {}
    
    for feature in available_categorical:
        if feature in encoded_data.columns:
            le = LabelEncoder()
            encoded_data[f'{feature}_encoded'] = le.fit_transform(encoded_data[feature].astype(str))
            label_encoders[feature] = le
            
            # Get unique categories
            categories = le.classes_
            print(f"   ✅ {feature}: {len(categories)} categories")
            if len(categories) <= 10:
                for i, cat in enumerate(categories):
                    print(f"      {i}: {cat}")
    
    # Step 7: Prepare final features for modeling
    print(f"\n🎯 Preparing final modeling dataset...")
    
    # Features for modeling (numerical + encoded categorical)
    model_features = available_numerical + [f'{f}_encoded' for f in available_categorical]
    
    X = encoded_data[model_features]
    y = encoded_data['first_year_revenue']
    
    # Additional columns for output requirements
    user_info = encoded_data[['user_id', 'country', 'first_event_date']]
    
    print(f"   Feature matrix X: {X.shape}")
    print(f"   Target vector y: {y.shape}")
    print(f"   User info: {user_info.shape}")
    
    # Step 8: Train/test split
    print(f"\n📊 Creating train/test split...")
    
    # Stratified split based on revenue categories
    revenue_bins = pd.cut(y, bins=[-np.inf, 0, 10, 50, np.inf], labels=['Zero', 'Low', 'Medium', 'High'])
    
    X_train, X_test, y_train, y_test, info_train, info_test = train_test_split(
        X, y, user_info, 
        test_size=0.2, 
        random_state=42, 
        stratify=revenue_bins
    )
    
    print(f"   Train set: {X_train.shape[0]:,} samples")
    print(f"   Test set: {X_test.shape[0]:,} samples")
    print(f"   Features: {X_train.shape[1]} features")
    
    # Train set stats
    print(f"\n   Train set target stats:")
    print(f"      Mean: ${y_train.mean():.2f}")
    print(f"      Non-zero: {(y_train > 0).sum():,} ({(y_train > 0).mean()*100:.2f}%)")
    
    print(f"\n   Test set target stats:")
    print(f"      Mean: ${y_test.mean():.2f}")
    print(f"      Non-zero: {(y_test > 0).sum():,} ({(y_test > 0).mean()*100:.2f}%)")
    
    # Step 9: Save datasets
    print(f"\n💾 Saving datasets...")
    
    # Combine features and target for saving
    train_dataset = pd.concat([X_train, y_train, info_train], axis=1)
    test_dataset = pd.concat([X_test, y_test, info_test], axis=1)
    
    # Save to CSV
    train_dataset.to_csv('../data/train_dataset.csv', index=False)
    test_dataset.to_csv('../data/test_dataset.csv', index=False)
    
    print(f"   ✅ Saved train_dataset.csv: {train_dataset.shape}")
    print(f"   ✅ Saved test_dataset.csv: {test_dataset.shape}")
    
    # Save feature information
    feature_info = {
        'numerical_features': available_numerical,
        'categorical_features': available_categorical,
        'encoded_categorical_features': [f'{f}_encoded' for f in available_categorical],
        'model_features': model_features,
        'label_encoders': {k: list(v.classes_) for k, v in label_encoders.items()},
        'target_variable': 'first_year_revenue',
        'dataset_stats': {
            'total_samples': len(final_data),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'num_features': len(model_features),
            'target_mean': float(y.mean()),
            'target_std': float(y.std()),
            'paying_users_pct': float((y > 0).mean() * 100)
        }
    }
    
    with open('../data/feature_info.json', 'w') as f:
        json.dump(feature_info, f, indent=2)
    
    print(f"   ✅ Saved feature_info.json")
    
    print(f"\n🎉 DATASET PREPARATION COMPLETED!")
    print("="*60)
    print(f"✅ Ready for model training with {len(model_features)} features")
    print(f"✅ Train/test split: {len(X_train):,}/{len(X_test):,} samples")
    print(f"✅ All files saved in model_training/data/")
    
    return {
        'X_train': X_train,
        'X_test': X_test,
        'y_train': y_train,
        'y_test': y_test,
        'feature_info': feature_info,
        'label_encoders': label_encoders
    }

if __name__ == "__main__":
    result = prepare_ltv_dataset()
