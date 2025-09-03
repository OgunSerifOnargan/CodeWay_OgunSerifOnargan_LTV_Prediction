# LTV Prediction Pipeline

This pipeline contains all the functional scripts used for the LTV prediction project, organized by purpose.

## 📁 Directory Structure

### `data_cleaning/`
Scripts for cleaning and preparing raw data:
- `load_parquet_to_postgres_chunked.py` - Load parquet file to PostgreSQL database
- `handle_null_values_simple.py` - Handle NULL values in dataset
- `remove_extra_columns.py` - Remove unnecessary columns

### `EDA/`
Exploratory Data Analysis scripts:
- `analyze_null_values.py` - Analyze NULL value patterns
- `check_data_timespan.py` - Check temporal data coverage
- `analyze_user_first_15_days.py` - Analyze user behavior in first 15 days
- `analyze_event_names.py` - Analyze event name patterns
- `analyze_event_time.py` - Analyze event timing patterns
- `analyze_multi_platform_users.py` - Analyze users across platforms
- `check_user_country_consistency.py` - Check country data consistency

### `feature_creation/`
Feature engineering scripts (creates database tables):
- `create_revenue_features_parallel.py` - Create revenue-based features
- `create_post_subscription_features_table.py` - Post-subscription behavior features
- `create_pre_subscription_features_ultra_fast.py` - Pre-subscription behavior features
- `create_rfm_features_table.py` - RFM (Recency, Frequency, Monetary) features
- `create_country_revenue_features_15days.py` - Country-based features
- `create_event_name_features_parallel.py` - Event name pattern features
- `create_non_paying_features_fast.py` - Non-paying user identification features
- `consolidate_features.py` - Merge all feature tables into one

### `model_training/`
Machine learning model scripts:
- `prepare_dataset.py` - Prepare final dataset for training
- `train_models.py` - Train multiple ML models
- `predict_ltv.py` - Generate predictions
- `save_test_results.py` - Save predictions to database
- `generate_evaluation_report.py` - Generate model evaluation report

### `garbage/`
Obsolete/duplicate scripts (kept for reference):
- Old versions of scripts that were replaced by optimized versions
- Experimental scripts that didn't make it to production

## 🚀 Pipeline Execution Order

1. **Data Loading & Cleaning**
   ```bash
   python data_cleaning/load_parquet_to_postgres_chunked.py
   python data_cleaning/handle_null_values_simple.py
   python data_cleaning/remove_extra_columns.py
   ```

2. **Exploratory Data Analysis** (Optional)
   ```bash
   python EDA/analyze_null_values.py
   python EDA/check_data_timespan.py
   python EDA/analyze_event_names.py
   # ... other EDA scripts as needed
   ```

3. **Feature Engineering**
   ```bash
   python feature_creation/create_revenue_features_parallel.py
   python feature_creation/create_post_subscription_features_table.py
   python feature_creation/create_pre_subscription_features_ultra_fast.py
   python feature_creation/create_rfm_features_table.py
   python feature_creation/create_country_revenue_features_15days.py
   python feature_creation/create_event_name_features_parallel.py
   python feature_creation/create_non_paying_features_fast.py
   python feature_creation/consolidate_features.py
   ```

4. **Model Training & Prediction**
   ```bash
   python model_training/prepare_dataset.py
   python model_training/train_models.py
   python model_training/predict_ltv.py
   python model_training/save_test_results.py
   python model_training/generate_evaluation_report.py
   ```

## 🗄️ Database Tables Created

| Table Name | Created By | Purpose |
|------------|------------|---------|
| `raw_dataset` | data_cleaning/load_parquet_to_postgres_chunked.py | Raw event data |
| `revenue_features` | feature_creation/create_revenue_features_parallel.py | Revenue-based features |
| `post_subscription_features` | feature_creation/create_post_subscription_features_table.py | Post-subscription behavior |
| `pre_subscription_features` | feature_creation/create_pre_subscription_features_ultra_fast.py | Pre-subscription behavior |
| `rfm_features` | feature_creation/create_rfm_features_table.py | RFM analysis features |
| `country_features` | feature_creation/create_country_revenue_features_15days.py | Country-based features |
| `event_name_features` | feature_creation/create_event_name_features_parallel.py | Event pattern features |
| `non_paying_user_features` | feature_creation/create_non_paying_features_fast.py | Non-paying user features |
| `consolidated_features` | feature_creation/consolidate_features.py | All features merged |
| `test_predictions` | model_training/save_test_results.py | Model predictions |

## ⚙️ Requirements

- Python 3.8+
- PostgreSQL database
- Required packages: pandas, numpy, scikit-learn, lightgbm, xgboost, polars, sqlalchemy, psycopg2, tqdm

## 📊 Expected Output

The pipeline generates:
1. Clean dataset in PostgreSQL
2. Feature tables with engineered features
3. Trained ML models (saved as pickle files)
4. Prediction results in database
5. Evaluation reports in Markdown format
6. Visualization plots (PNG files)

## 🔧 Configuration

Update database connection string in each script:
```python
DB_URL = 'postgresql://username@localhost:5432/database_name'
```
