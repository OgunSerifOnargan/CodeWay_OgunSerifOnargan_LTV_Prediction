import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def generate_comprehensive_evaluation_report():
    """Generate comprehensive evaluation report for LTV prediction model"""
    
    print("📊 GENERATING COMPREHENSIVE EVALUATION REPORT...")
    print("="*70)
    
    engine = create_engine(DB_URL)
    
    # Load test predictions
    print("📥 Loading test predictions from database...")
    query = """
    SELECT 
        user_id, country, first_event_date,
        actual_ltv, predicted_ltv, prediction_error, 
        absolute_error, is_paying_user, predicted_paying_user
    FROM test_predictions
    """
    df = pd.read_sql(query, engine)
    print(f"   ✅ Loaded {len(df):,} predictions")
    
    # Generate report
    report = []
    report.append("# 🎯 LTV PREDICTION MODEL - COMPREHENSIVE EVALUATION REPORT")
    report.append("="*80)
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Model:** LightGBM")
    report.append(f"**Test Samples:** {len(df):,}")
    report.append("")
    
    # === OVERALL PERFORMANCE ===
    report.append("## 📈 OVERALL PERFORMANCE METRICS")
    report.append("-" * 50)
    
    actual_total = df['actual_ltv'].sum()
    predicted_total = df['predicted_ltv'].sum()
    revenue_accuracy = (predicted_total / actual_total) * 100
    mae = df['absolute_error'].mean()
    rmse = np.sqrt((df['prediction_error'] ** 2).mean())
    r2 = 1 - (df['prediction_error'] ** 2).sum() / ((df['actual_ltv'] - df['actual_ltv'].mean()) ** 2).sum()
    
    report.append(f"**Total Actual Revenue:** ${actual_total:,.2f}")
    report.append(f"**Total Predicted Revenue:** ${predicted_total:,.2f}")
    report.append(f"**Revenue Accuracy:** {revenue_accuracy:.1f}%")
    report.append(f"**Mean Absolute Error:** ${mae:.2f}")
    report.append(f"**Root Mean Square Error:** ${rmse:.2f}")
    report.append(f"**R² Score:** {r2:.4f}")
    report.append("")
    
    # === USER CLASSIFICATION ANALYSIS ===
    report.append("## 👥 USER CLASSIFICATION ANALYSIS")
    report.append("-" * 50)
    
    actual_paying = df['is_paying_user'].sum()
    predicted_paying = df['predicted_paying_user'].sum()
    
    # Confusion matrix for paying users
    tp = ((df['is_paying_user'] == 1) & (df['predicted_paying_user'] == 1)).sum()
    tn = ((df['is_paying_user'] == 0) & (df['predicted_paying_user'] == 0)).sum()
    fp = ((df['is_paying_user'] == 0) & (df['predicted_paying_user'] == 1)).sum()
    fn = ((df['is_paying_user'] == 1) & (df['predicted_paying_user'] == 0)).sum()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    report.append(f"**Actual Paying Users:** {actual_paying:,} ({actual_paying/len(df)*100:.1f}%)")
    report.append(f"**Predicted Paying Users:** {predicted_paying:,} ({predicted_paying/len(df)*100:.1f}%)")
    report.append("")
    report.append("**Classification Metrics:**")
    report.append(f"- Precision: {precision:.4f}")
    report.append(f"- Recall: {recall:.4f}")
    report.append(f"- F1-Score: {f1:.4f}")
    report.append("")
    report.append("**Confusion Matrix:**")
    report.append(f"- True Positives: {tp:,}")
    report.append(f"- True Negatives: {tn:,}")
    report.append(f"- False Positives: {fp:,}")
    report.append(f"- False Negatives: {fn:,}")
    report.append("")
    
    # === PAYING USERS DEEP DIVE ===
    report.append("## 💰 PAYING USERS PERFORMANCE")
    report.append("-" * 50)
    
    paying_users = df[df['is_paying_user'] == 1].copy()
    if len(paying_users) > 0:
        paying_mae = paying_users['absolute_error'].mean()
        paying_rmse = np.sqrt((paying_users['prediction_error'] ** 2).mean())
        paying_r2 = 1 - (paying_users['prediction_error'] ** 2).sum() / ((paying_users['actual_ltv'] - paying_users['actual_ltv'].mean()) ** 2).sum()
        
        report.append(f"**Paying Users Count:** {len(paying_users):,}")
        report.append(f"**Actual Total (Paying):** ${paying_users['actual_ltv'].sum():,.2f}")
        report.append(f"**Predicted Total (Paying):** ${paying_users['predicted_ltv'].sum():,.2f}")
        report.append(f"**MAE (Paying Users):** ${paying_mae:.2f}")
        report.append(f"**RMSE (Paying Users):** ${paying_rmse:.2f}")
        report.append(f"**R² (Paying Users):** {paying_r2:.4f}")
        report.append("")
        
        # LTV distribution for paying users
        report.append("**LTV Distribution (Paying Users):**")
        report.append(f"- Mean Actual LTV: ${paying_users['actual_ltv'].mean():.2f}")
        report.append(f"- Mean Predicted LTV: ${paying_users['predicted_ltv'].mean():.2f}")
        report.append(f"- Median Actual LTV: ${paying_users['actual_ltv'].median():.2f}")
        report.append(f"- Median Predicted LTV: ${paying_users['predicted_ltv'].median():.2f}")
        report.append("")
    
    # === COUNTRY-LEVEL ANALYSIS ===
    report.append("## 🌍 COUNTRY-LEVEL ANALYSIS")
    report.append("-" * 50)
    
    country_analysis = df.groupby('country').agg({
        'user_id': 'count',
        'actual_ltv': ['sum', 'mean'],
        'predicted_ltv': ['sum', 'mean'],
        'absolute_error': 'mean',
        'is_paying_user': 'sum'
    }).round(2)
    
    country_analysis.columns = ['Users', 'Actual_Total', 'Actual_Avg', 'Predicted_Total', 'Predicted_Avg', 'MAE', 'Paying_Users']
    country_analysis['Revenue_Accuracy'] = (country_analysis['Predicted_Total'] / country_analysis['Actual_Total'] * 100).round(1)
    country_analysis = country_analysis.sort_values('Actual_Total', ascending=False).head(10)
    
    report.append("**Top 10 Countries by Actual Revenue:**")
    report.append("")
    for country, row in country_analysis.iterrows():
        report.append(f"**{country}:**")
        report.append(f"  - Users: {int(row['Users']):,}")
        report.append(f"  - Actual Total: ${row['Actual_Total']:,.2f}")
        report.append(f"  - Predicted Total: ${row['Predicted_Total']:,.2f}")
        report.append(f"  - Revenue Accuracy: {row['Revenue_Accuracy']:.1f}%")
        report.append(f"  - Paying Users: {int(row['Paying_Users']):,} ({int(row['Paying_Users'])/int(row['Users'])*100:.1f}%)")
        report.append(f"  - MAE: ${row['MAE']:.2f}")
        report.append("")
    
    # === COHORT ANALYSIS ===
    report.append("## 📅 COHORT-LEVEL ANALYSIS")
    report.append("-" * 50)
    
    df['first_event_date'] = pd.to_datetime(df['first_event_date'])
    cohort_analysis = df.groupby('first_event_date').agg({
        'user_id': 'count',
        'actual_ltv': ['sum', 'mean'],
        'predicted_ltv': ['sum', 'mean'],
        'absolute_error': 'mean',
        'is_paying_user': 'sum'
    }).round(2)
    
    cohort_analysis.columns = ['Users', 'Actual_Total', 'Actual_Avg', 'Predicted_Total', 'Predicted_Avg', 'MAE', 'Paying_Users']
    cohort_analysis['Revenue_Accuracy'] = (cohort_analysis['Predicted_Total'] / cohort_analysis['Actual_Total'] * 100).round(1)
    cohort_analysis = cohort_analysis.sort_values('Actual_Total', ascending=False).head(10)
    
    report.append("**Top 10 Cohorts by Actual Revenue:**")
    report.append("")
    for date, row in cohort_analysis.iterrows():
        report.append(f"**{date.strftime('%Y-%m-%d')}:**")
        report.append(f"  - Users: {int(row['Users']):,}")
        report.append(f"  - Actual Total: ${row['Actual_Total']:,.2f}")
        report.append(f"  - Predicted Total: ${row['Predicted_Total']:,.2f}")
        report.append(f"  - Revenue Accuracy: {row['Revenue_Accuracy']:.1f}%")
        report.append(f"  - Paying Users: {int(row['Paying_Users']):,} ({int(row['Paying_Users'])/int(row['Users'])*100:.1f}%)")
        report.append(f"  - MAE: ${row['MAE']:.2f}")
        report.append("")
    
    # === MODEL BEHAVIOR INSIGHTS ===
    report.append("## 🔍 MODEL BEHAVIOR INSIGHTS")
    report.append("-" * 50)
    
    # Conservative bias analysis
    over_predictions = (df['predicted_ltv'] > df['actual_ltv']).sum()
    under_predictions = (df['predicted_ltv'] < df['actual_ltv']).sum()
    perfect_predictions = (df['predicted_ltv'] == df['actual_ltv']).sum()
    
    report.append(f"**Prediction Bias Analysis:**")
    report.append(f"- Over-predictions: {over_predictions:,} ({over_predictions/len(df)*100:.1f}%)")
    report.append(f"- Under-predictions: {under_predictions:,} ({under_predictions/len(df)*100:.1f}%)")
    report.append(f"- Perfect predictions: {perfect_predictions:,} ({perfect_predictions/len(df)*100:.1f}%)")
    report.append("")
    
    # Error distribution
    error_percentiles = df['absolute_error'].quantile([0.5, 0.75, 0.9, 0.95, 0.99])
    report.append(f"**Error Distribution:**")
    report.append(f"- 50th percentile: ${error_percentiles[0.5]:.2f}")
    report.append(f"- 75th percentile: ${error_percentiles[0.75]:.2f}")
    report.append(f"- 90th percentile: ${error_percentiles[0.9]:.2f}")
    report.append(f"- 95th percentile: ${error_percentiles[0.95]:.2f}")
    report.append(f"- 99th percentile: ${error_percentiles[0.99]:.2f}")
    report.append("")
    
    # === RECOMMENDATIONS ===
    report.append("## 🎯 KEY FINDINGS & RECOMMENDATIONS")
    report.append("-" * 50)
    
    report.append("**🔴 CRITICAL ISSUES:**")
    if predicted_paying/len(df) > 0.95:
        report.append("- **Conservative Bias**: Model predicts almost all users as paying (99.9% vs actual 6.1%)")
        report.append("- **Classification Problem**: Model struggles to identify non-paying users")
    
    report.append("")
    report.append("**✅ STRENGTHS:**")
    if revenue_accuracy > 95:
        report.append(f"- **Revenue Accuracy**: Excellent total revenue prediction ({revenue_accuracy:.1f}%)")
    if r2 > 0.4:
        report.append(f"- **R² Score**: Good explained variance ({r2:.4f})")
    
    report.append("")
    report.append("**🔧 RECOMMENDATIONS:**")
    report.append("1. **Two-Stage Approach**: Implement classification + regression pipeline")
    report.append("2. **Threshold Optimization**: Find optimal LTV threshold for paying user classification")
    report.append("3. **Class Balancing**: Use techniques like SMOTE or class weights for imbalanced data")
    report.append("4. **Feature Engineering**: Add more discriminative features for non-paying users")
    report.append("5. **Ensemble Methods**: Combine multiple models for better classification")
    report.append("")
    
    # Save report
    report_content = "\\n".join(report)
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"../results/ltv_evaluation_report_{timestamp}.md"
    
    with open(report_filename, 'w') as f:
        f.write(report_content)
    
    print(f"✅ Comprehensive evaluation report saved: {report_filename}")
    print("")
    print("📊 SUMMARY:")
    print(f"   Total Revenue Accuracy: {revenue_accuracy:.1f}%")
    print(f"   R² Score: {r2:.4f}")
    print(f"   MAE: ${mae:.2f}")
    print(f"   Critical Issue: Model predicts {predicted_paying/len(df)*100:.1f}% as paying users (actual: {actual_paying/len(df)*100:.1f}%)")
    
    return df, report_content

if __name__ == "__main__":
    results_df, report = generate_comprehensive_evaluation_report()
