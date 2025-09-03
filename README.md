# LTV Prediction Project

## Summary

<!-- Summary section - to be filled later -->

![Cohort Revenue Comparison](final/model_training/results/cohort_revenue_comparison_with_OS.png)

---

## Task Description

### Q1: LTV Prediction

Business teams have approached the Data Science team with a request. They want you to predict 1-year revenue of the users based on their first 15 days of app engagement. The reason is to estimate user-level as well as cohort level revenues from marketing campaigns. Please note that the users who downloaded the app (a.k.a. first event date) on the same day are considered in the same cohort. This prediction will enable the business team to understand the high-revenue or low-retention cohorts from really early days so that they can apply campaign optimization, budget allocation and smarter marketing strategies.

They have provided you with a dataset named 'ltvprediction_case.parquet' for our app, XYZ. This dataset includes each user's events for the first 15 days after downloading the app.

---

## Questions and Answers

### a. Create a feature set from the given dataset. Provide explanations and intuitions for the features you create.

**Answer:**

Our comprehensive feature engineering approach covers multiple aspects of user behavior analysis:

- **[Comprehensive Feature Engineering Report](final/ara_raporlar/comprehensive_feature_engineering_report.md)** - Main feature engineering documentation with detailed explanations and business intuition for all created features
- **[Data Exploration Analysis](final/ara_raporlar/data_exploration_analysis_report.md)** - Exploratory data analysis covering all dataset columns and patterns
- **[Operating System Analysis](final/ara_raporlar/OPERATING_SYSTEM_ANALYSIS_SUMMARY.md)** - Platform-specific behavior analysis and feature creation
- **[Country Clustering Analysis](final/ara_raporlar/country_clustering_summary_k4.md)** - Geographic segmentation and country-tier feature engineering
- **[Revenue Timeline Analysis](final/ara_raporlar/15_day_revenue_timeline_report.md)** - Temporal revenue pattern analysis
- **[Data Leakage Analysis](final/ara_raporlar/final_data_leakage_analysis.md)** - Comprehensive data integrity verification

**Key Feature Categories:**
- **Revenue Features**: Total, average, per-event revenue metrics with volatility and risk indicators
- **RFM Features**: Recency, Frequency, Monetary analysis for user engagement patterns
- **Subscription Features**: Pre/post-subscription behavior, renewal patterns, trial usage
- **Behavioral Features**: Event sequences, paywall interactions, engagement depth
- **Geographic Features**: Country-tier clustering based on revenue performance
- **Operating System Features**: Platform-specific behavior and conversion patterns
- **Non-Paying User Features**: Specialized features to identify users with zero LTV

---

### b. Build a model to predict 1-year revenue. Expected outcomes include: exploratory data analysis, pipeline creation, feature importance, and evaluation.

**Answer:**

Our model building approach follows industry best practices with comprehensive evaluation:

- **[Model Training & Evaluation Report](final/ara_raporlar/model_training_evaluation_report.md)** - Complete model development process including algorithm comparison, hyperparameter tuning, and performance metrics
- **[Pipeline Development Report](final/ara_raporlar/model_building_pipeline_development_report.md)** - Technical implementation details of the ML pipeline

**Key Achievements:**
- **Best Model**: LightGBM with 25 carefully selected features
- **Performance**: R² = 0.4567, RMSE = $14.23, Revenue Accuracy = 98.4%
- **Feature Selection**: Correlation analysis, VIF testing, and domain expertise
- **Pipeline**: Fully automated, vectorized pandas operations, SQL optimization
- **Scalability**: Chunked processing for large datasets, parallel feature engineering

---

### c. We expect you to provide a thorough evaluation on predictions on user-level and cohort-level separately. Use your creativity to build evaluation pipelines (charts, metrics, a/b testing schemas).

**Answer:**

Our evaluation framework provides comprehensive assessment across multiple dimensions:

- **[Comprehensive Prediction Evaluation Report](final/ara_raporlar/comprehensive_prediction_evaluation_report.md)** - Detailed user-level and cohort-level evaluation with statistical significance testing

**Cohort-Level Analysis:**
![Cohort Revenue Comparison](final/model_training/results/cohort_revenue_comparison_with_OS.png)

**Key Evaluation Components:**
- **User-Level Metrics**: Individual prediction accuracy, error distribution, confidence intervals
- **Cohort-Level Metrics**: Temporal stability, revenue estimation accuracy, statistical significance
- **Business Impact Assessment**: Marketing campaign optimization potential, budget allocation insights
- **Advanced Pipelines**: A/B testing frameworks, composite evaluation scores, platform-specific analysis
- **Statistical Validation**: T-tests, confidence intervals, temporal consistency checks

**Performance Highlights:**
- **User-Level**: 98.4% revenue accuracy, effective high-value user identification
- **Cohort-Level**: 98.4% total revenue prediction accuracy, consistent temporal performance
- **Business Value**: Enables early intervention strategies and optimized marketing spend

---

### d. You will be instrumental on our data science team that constantly builds pipelines and improves our infrastructure. Therefore, we value and expect solid software engineering principles.

**Answer:**

Our pipeline demonstrates enterprise-grade software engineering practices:

- **[Pipeline Development Report](final/ara_raporlar/model_building_pipeline_development_report.md)** - Complete technical documentation of our ML infrastructure

**Software Engineering Highlights:**

**🚀 Pipeline Architecture:**
- **Modular Design**: Separate stages for data cleaning, feature engineering, model training, and evaluation
- **Vectorized Operations**: All data processing uses vectorized pandas operations for optimal performance
- **SQL Optimization**: Efficient database queries with proper indexing and chunked operations
- **Error Handling**: Comprehensive exception handling and logging throughout the pipeline
- **Scalability**: Designed to handle datasets of any size with memory-efficient processing

**🔧 Technical Implementation:**
- **Language Stack**: Python, SQL, Pandas (vectorized operations)
- **Database**: PostgreSQL with optimized queries and indexing
- **Processing**: Chunked data loading, parallel feature engineering, memory-efficient operations
- **Testing**: Comprehensive data validation and model performance testing
- **Documentation**: Detailed technical documentation and code comments

**📊 Performance Optimization:**
- **Data Loading**: 9,311 rows/second with chunked parquet processing
- **Feature Engineering**: Parallel processing with vectorized pandas operations
- **Model Training**: Efficient hyperparameter tuning and cross-validation
- **Prediction**: Batch prediction with optimized memory usage

**🔍 Code Quality:**
- **Modular Functions**: Reusable components for different pipeline stages
- **Version Control**: Git-based development with proper branching
- **Configuration Management**: Centralized parameter management
- **Monitoring**: Performance tracking and error logging

---

### e. Required output columns: user_id, country, first_event_date, predicted_ltv

**Output File:**
- **Path**: `final/results/ltv_predictions_output.parquet`
- **Format**: Parquet (optimized for data science workflows)
- **Records**: 439,978 user predictions
- **Columns**: 
  - `user_id`: Unique user identifier
  - `country`: User's country code
  - `first_event_date`: Date of first app engagement
  - `predicted_ltv`: Predicted 1-year revenue in USD

**Sample Output:**
```
          user_id country first_event_date  predicted_ltv
0  012A0000D4D4-2      CA       2022-10-21       0.219398
1  707262621818-3      IN       2022-11-16       0.351159
2  D64D9A9A3131-7      US       2022-12-12       0.729476
3  CFF0A8A87474-B      US       2022-11-25       7.176606
4  675F47471515-5      AU       2022-09-25       6.373198
```

---

## Technical Stack

- **Languages**: Python, SQL
- **Data Processing**: Pandas (vectorized operations), NumPy
- **Database**: PostgreSQL
- **Machine Learning**: LightGBM, XGBoost, Random Forest, Linear Regression
- **Visualization**: Matplotlib, Seaborn
- **Infrastructure**: Modular pipeline architecture with error handling and logging

---

## Repository Structure

```
├── final/
│   ├── ara_raporlar/                    # Analysis reports
│   ├── pipeline/                        # ML pipeline code
│   │   ├── data_cleaning/              # Data preprocessing
│   │   ├── feature_creation/           # Feature engineering
│   │   ├── model_training/             # Model development
│   │   └── EDA/                        # Exploratory data analysis
│   ├── results/                         # Output files
│   └── model_training/results/          # Model artifacts and visualizations
├── ltvprediction_case.parquet          # Original dataset
└── README.md                           # This file
```

---

## Getting Started

1. **Environment Setup**: Install required dependencies
2. **Data Loading**: Run the data cleaning pipeline
3. **Feature Engineering**: Execute feature creation scripts
4. **Model Training**: Train and evaluate models
5. **Prediction**: Generate LTV predictions for new users

For detailed technical implementation, refer to the [Pipeline Development Report](final/ara_raporlar/model_building_pipeline_development_report.md).
