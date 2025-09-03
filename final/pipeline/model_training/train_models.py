import pandas as pd
import numpy as np
import json
import pickle
import warnings
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# Machine Learning libraries
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

# XGBoost and LightGBM
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️ XGBoost not available")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("⚠️ LightGBM not available")

warnings.filterwarnings('ignore')

def load_datasets():
    """Load prepared train and test datasets"""
    
    print("📥 Loading datasets...")
    
    # Load datasets
    train_data = pd.read_csv('../data/train_dataset.csv')
    test_data = pd.read_csv('../data/test_dataset.csv')
    
    # Load feature info
    with open('../data/feature_info.json', 'r') as f:
        feature_info = json.load(f)
    
    model_features = feature_info['model_features']
    
    # Separate features and target
    X_train = train_data[model_features]
    y_train = train_data['first_year_revenue']
    X_test = test_data[model_features]
    y_test = test_data['first_year_revenue']
    
    # User info for final predictions
    user_info_test = test_data[['user_id', 'country', 'first_event_date']]
    
    print(f"   ✅ Train: {X_train.shape[0]:,} samples, {X_train.shape[1]} features")
    print(f"   ✅ Test: {X_test.shape[0]:,} samples, {X_test.shape[1]} features")
    
    return X_train, X_test, y_train, y_test, user_info_test, feature_info

def calculate_metrics(y_true, y_pred, model_name="Model"):
    """Calculate comprehensive regression metrics"""
    
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    
    # Additional metrics for revenue prediction
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100  # Avoid division by zero
    
    # Revenue-specific metrics
    total_actual = y_true.sum()
    total_predicted = y_pred.sum()
    revenue_accuracy = 1 - abs(total_actual - total_predicted) / total_actual
    
    # Paying users accuracy
    actual_paying = (y_true > 0).sum()
    predicted_paying = (y_pred > 0).sum()
    paying_accuracy = 1 - abs(actual_paying - predicted_paying) / actual_paying if actual_paying > 0 else 0
    
    metrics = {
        'model': model_name,
        'mse': mse,
        'rmse': rmse,
        'mae': mae,
        'r2': r2,
        'mape': mape,
        'revenue_accuracy': revenue_accuracy,
        'paying_accuracy': paying_accuracy,
        'total_actual_revenue': total_actual,
        'total_predicted_revenue': total_predicted,
        'actual_paying_users': actual_paying,
        'predicted_paying_users': predicted_paying
    }
    
    return metrics

def train_linear_models(X_train, X_test, y_train, y_test):
    """Train Linear Regression and Ridge Regression models"""
    
    print("\n🔵 TRAINING LINEAR MODELS...")
    print("-" * 50)
    
    # Scale features for linear models
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {}
    results = []
    
    # Linear Regression
    print("   Training Linear Regression...")
    lr_model = LinearRegression()
    lr_model.fit(X_train_scaled, y_train)
    
    lr_pred = lr_model.predict(X_test_scaled)
    lr_metrics = calculate_metrics(y_test, lr_pred, "Linear Regression")
    results.append(lr_metrics)
    
    models['linear_regression'] = {
        'model': lr_model,
        'scaler': scaler,
        'predictions': lr_pred
    }
    
    print(f"      ✅ RMSE: ${lr_metrics['rmse']:.2f}, R²: {lr_metrics['r2']:.4f}")
    
    # Ridge Regression
    print("   Training Ridge Regression...")
    ridge_model = Ridge(alpha=1.0, random_state=42)
    ridge_model.fit(X_train_scaled, y_train)
    
    ridge_pred = ridge_model.predict(X_test_scaled)
    ridge_metrics = calculate_metrics(y_test, ridge_pred, "Ridge Regression")
    results.append(ridge_metrics)
    
    models['ridge_regression'] = {
        'model': ridge_model,
        'scaler': scaler,
        'predictions': ridge_pred
    }
    
    print(f"      ✅ RMSE: ${ridge_metrics['rmse']:.2f}, R²: {ridge_metrics['r2']:.4f}")
    
    return models, results

def train_tree_models(X_train, X_test, y_train, y_test):
    """Train tree-based models (Random Forest, XGBoost, LightGBM)"""
    
    print("\n🌳 TRAINING TREE-BASED MODELS...")
    print("-" * 50)
    
    models = {}
    results = []
    
    # Random Forest
    print("   Training Random Forest...")
    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    
    rf_pred = rf_model.predict(X_test)
    rf_metrics = calculate_metrics(y_test, rf_pred, "Random Forest")
    results.append(rf_metrics)
    
    models['random_forest'] = {
        'model': rf_model,
        'predictions': rf_pred,
        'feature_importance': rf_model.feature_importances_
    }
    
    print(f"      ✅ RMSE: ${rf_metrics['rmse']:.2f}, R²: {rf_metrics['r2']:.4f}")
    
    # XGBoost
    if XGBOOST_AVAILABLE:
        print("   Training XGBoost...")
        xgb_model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        xgb_model.fit(X_train, y_train)
        
        xgb_pred = xgb_model.predict(X_test)
        xgb_metrics = calculate_metrics(y_test, xgb_pred, "XGBoost")
        results.append(xgb_metrics)
        
        models['xgboost'] = {
            'model': xgb_model,
            'predictions': xgb_pred,
            'feature_importance': xgb_model.feature_importances_
        }
        
        print(f"      ✅ RMSE: ${xgb_metrics['rmse']:.2f}, R²: {xgb_metrics['r2']:.4f}")
    
    # LightGBM
    if LIGHTGBM_AVAILABLE:
        print("   Training LightGBM...")
        lgb_model = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        lgb_model.fit(X_train, y_train)
        
        lgb_pred = lgb_model.predict(X_test)
        lgb_metrics = calculate_metrics(y_test, lgb_pred, "LightGBM")
        results.append(lgb_metrics)
        
        models['lightgbm'] = {
            'model': lgb_model,
            'predictions': lgb_pred,
            'feature_importance': lgb_model.feature_importances_
        }
        
        print(f"      ✅ RMSE: ${lgb_metrics['rmse']:.2f}, R²: {lgb_metrics['r2']:.4f}")
    
    return models, results

def save_models(models):
    """Save trained models"""
    
    print("\n💾 SAVING MODELS...")
    print("-" * 50)
    
    for model_name, model_data in models.items():
        filename = f"../models/{model_name}_model.pkl"
        
        with open(filename, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"   ✅ Saved {model_name}_model.pkl")

def create_model_comparison(all_results):
    """Create comprehensive model comparison"""
    
    print("\n📊 MODEL COMPARISON RESULTS...")
    print("-" * 50)
    
    # Convert to DataFrame
    results_df = pd.DataFrame(all_results)
    
    # Sort by R² score (descending)
    results_df = results_df.sort_values('r2', ascending=False)
    
    print("🏆 MODEL PERFORMANCE RANKING:")
    print("="*80)
    
    for i, (_, row) in enumerate(results_df.iterrows(), 1):
        print(f"{i:2d}. {row['model']:<20}")
        print(f"    RMSE: ${row['rmse']:>8.2f}  |  MAE: ${row['mae']:>8.2f}  |  R²: {row['r2']:>7.4f}")
        print(f"    Revenue Accuracy: {row['revenue_accuracy']*100:>5.1f}%  |  MAPE: {row['mape']:>6.2f}%")
        print(f"    Total Revenue: ${row['total_predicted_revenue']:>12,.2f} (Actual: ${row['total_actual_revenue']:>12,.2f})")
        print()
    
    # Save results
    results_df.to_csv('../results/model_comparison.csv', index=False)
    print("   ✅ Saved model_comparison.csv")
    
    return results_df

def create_feature_importance_plot(models, feature_names):
    """Create feature importance plots for tree-based models"""
    
    print("\n📈 CREATING FEATURE IMPORTANCE PLOTS...")
    print("-" * 50)
    
    tree_models = {k: v for k, v in models.items() if 'feature_importance' in v}
    
    if not tree_models:
        print("   ⚠️ No tree-based models with feature importance found")
        return
    
    n_models = len(tree_models)
    fig, axes = plt.subplots(1, n_models, figsize=(6*n_models, 8))
    
    if n_models == 1:
        axes = [axes]
    
    for i, (model_name, model_data) in enumerate(tree_models.items()):
        importance = model_data['feature_importance']
        
        # Create DataFrame for plotting
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=True)
        
        # Plot
        axes[i].barh(importance_df['feature'], importance_df['importance'])
        axes[i].set_title(f'{model_name.replace("_", " ").title()}\nFeature Importance')
        axes[i].set_xlabel('Importance')
        
        # Rotate labels if needed
        axes[i].tick_params(axis='y', labelsize=8)
    
    plt.tight_layout()
    plt.savefig('../results/feature_importance.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("   ✅ Saved feature_importance.png")

def main():
    """Main training pipeline"""
    
    print("🚀 STARTING LTV MODEL TRAINING PIPELINE...")
    print("="*60)
    
    # Load datasets
    X_train, X_test, y_train, y_test, user_info_test, feature_info = load_datasets()
    
    # Store all models and results
    all_models = {}
    all_results = []
    
    # Train linear models
    linear_models, linear_results = train_linear_models(X_train, X_test, y_train, y_test)
    all_models.update(linear_models)
    all_results.extend(linear_results)
    
    # Train tree-based models
    tree_models, tree_results = train_tree_models(X_train, X_test, y_train, y_test)
    all_models.update(tree_models)
    all_results.extend(tree_results)
    
    # Save all models
    save_models(all_models)
    
    # Create model comparison
    results_df = create_model_comparison(all_results)
    
    # Create feature importance plots
    create_feature_importance_plot(all_models, feature_info['model_features'])
    
    # Select best model
    best_model_name = results_df.iloc[0]['model']
    best_r2 = results_df.iloc[0]['r2']
    best_rmse = results_df.iloc[0]['rmse']
    
    print(f"\n🏆 BEST MODEL: {best_model_name}")
    print(f"   R² Score: {best_r2:.4f}")
    print(f"   RMSE: ${best_rmse:.2f}")
    
    # Save training summary (convert numpy types to native Python types)
    training_summary = {
        'training_date': datetime.now().isoformat(),
        'dataset_info': {
            'train_samples': int(len(X_train)),
            'test_samples': int(len(X_test)),
            'features': int(len(feature_info['model_features'])),
            'feature_names': feature_info['model_features']
        },
        'best_model': {
            'name': best_model_name,
            'r2_score': float(best_r2),
            'rmse': float(best_rmse)
        },
        'all_results': [{k: float(v) if isinstance(v, (np.integer, np.floating)) else v 
                        for k, v in result.items()} for result in all_results]
    }
    
    with open('../results/training_summary.json', 'w') as f:
        json.dump(training_summary, f, indent=2)
    
    print(f"\n🎉 MODEL TRAINING COMPLETED!")
    print("="*60)
    print(f"✅ {len(all_models)} models trained and saved")
    print(f"✅ Best model: {best_model_name} (R²: {best_r2:.4f})")
    print(f"✅ Results saved in model_training/results/")
    
    return all_models, results_df, training_summary

if __name__ == "__main__":
    models, results, summary = main()
