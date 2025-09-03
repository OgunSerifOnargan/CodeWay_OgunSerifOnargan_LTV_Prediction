# LTV Prediction Model Training

This directory contains all scripts and resources for training the 1-year revenue prediction model.

## Directory Structure

```
model_training/
├── README.md                    # This file
├── data/                        # Prepared datasets
│   ├── train_dataset.csv       # Training data
│   ├── test_dataset.csv        # Test data
│   └── feature_info.json       # Feature descriptions
├── models/                      # Trained models
│   ├── xgboost_model.pkl       # XGBoost model
│   ├── lightgbm_model.pkl      # LightGBM model
│   ├── random_forest_model.pkl # Random Forest model
│   └── linear_model.pkl        # Linear Regression model
├── results/                     # Model results and evaluation
│   ├── model_comparison.csv    # Performance comparison
│   ├── feature_importance.png  # Feature importance plots
│   ├── predictions_analysis.png # Prediction analysis
│   └── evaluation_report.html  # Comprehensive evaluation
├── notebooks/                   # Jupyter notebooks (if needed)
└── scripts/                     # Training scripts
    ├── prepare_dataset.py      # Data preparation
    ├── train_models.py         # Model training
    ├── evaluate_models.py      # Model evaluation
    └── predict_ltv.py          # Prediction pipeline
```

## Selected Features (13 total)

### Numerical Features (7)
- `post_sub_revenue_efficiency` (r=0.622) - Ultra High Impact
- `subscriptions_started_15d` (r=0.509) - Ultra High Impact  
- `first_15_days_revenue_per_day` (r=0.455) - High Impact
- `revenue_volatility_in_first_15_days` (r=0.419) - High Impact
- `pre_sub_events_count` (r=0.381) - High Impact
- `post_sub_events_count` (r=0.360) - High Impact
- `days_since_trial_start` (r=0.267) - Medium Impact

### Categorical Features (6)
- `rfm_segment` - RFM customer segmentation
- `has_golden_pattern` - Golden engagement pattern flag
- `country_tier` - Country tier (High/Mid/Low)
- `revenue_pattern_risk_in_first_15_days` - Revenue risk pattern
- `is_churned` - Churn status
- `has_refund_in_first_15_days` - Refund flag

## Target Variable
- `first_year_revenue` - 1-year revenue prediction target

## Model Pipeline
1. **Data Preparation** - Load and prepare final dataset
2. **Feature Engineering** - Encode categorical variables
3. **Train/Test Split** - Split data for training and validation
4. **Model Training** - Train multiple models (XGBoost, LightGBM, RF, Linear)
5. **Model Evaluation** - Compare performance metrics
6. **Model Selection** - Select best performing model
7. **Final Prediction** - Generate predictions with confidence intervals

## Usage
```bash
cd model_training
python scripts/prepare_dataset.py    # Prepare data
python scripts/train_models.py       # Train all models
python scripts/evaluate_models.py    # Evaluate and compare
python scripts/predict_ltv.py        # Generate predictions
```
