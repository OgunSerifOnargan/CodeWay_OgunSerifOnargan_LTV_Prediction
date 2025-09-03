import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sqlalchemy import create_engine
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def create_cohort_visualization():
    """Create cohort-level line graph comparing actual vs predicted revenue"""
    
    print("📊 CREATING COHORT-LEVEL REVENUE VISUALIZATION...")
    print("="*60)
    
    engine = create_engine(DB_URL)
    
    # Load test predictions with cohort grouping
    print("📥 Loading test predictions data...")
    query = """
    SELECT 
        first_event_date,
        COUNT(*) as user_count,
        SUM(actual_ltv) as total_actual_revenue,
        SUM(predicted_ltv) as total_predicted_revenue,
        AVG(actual_ltv) as avg_actual_ltv,
        AVG(predicted_ltv) as avg_predicted_ltv
    FROM test_prediction_with_OS
    GROUP BY first_event_date
    ORDER BY first_event_date
    """
    
    cohort_data = pd.read_sql(query, engine)
    print(f"✅ Loaded {len(cohort_data)} cohorts")
    
    # Convert first_event_date to datetime
    cohort_data['first_event_date'] = pd.to_datetime(cohort_data['first_event_date'])
    
    # Summary statistics
    print(f"\n📈 COHORT ANALYSIS SUMMARY:")
    print(f"   Date Range: {cohort_data['first_event_date'].min()} to {cohort_data['first_event_date'].max()}")
    print(f"   Total Cohorts: {len(cohort_data)}")
    print(f"   Total Users: {cohort_data['user_count'].sum():,}")
    print(f"   Total Actual Revenue: ${cohort_data['total_actual_revenue'].sum():,.2f}")
    print(f"   Total Predicted Revenue: ${cohort_data['total_predicted_revenue'].sum():,.2f}")
    print(f"   Overall Accuracy: {(cohort_data['total_predicted_revenue'].sum() / cohort_data['total_actual_revenue'].sum()) * 100:.1f}%")
    
    # Create the line graph
    plt.figure(figsize=(15, 8))
    
    # Plot actual vs predicted revenue
    plt.plot(cohort_data['first_event_date'], cohort_data['total_actual_revenue'], 
             label='Actual Revenue', linewidth=2, color='#1f77b4', marker='o', markersize=4)
    plt.plot(cohort_data['first_event_date'], cohort_data['total_predicted_revenue'], 
             label='Predicted Revenue', linewidth=2, color='#ff7f0e', marker='s', markersize=4)
    
    # Formatting
    plt.title('Cohort-Level Revenue Comparison: Actual vs Predicted\n(Operating System Features Included)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('First Event Date (Cohort)', fontsize=12, fontweight='bold')
    plt.ylabel('Total Revenue ($)', fontsize=12, fontweight='bold')
    
    # Format x-axis dates
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)
    
    # Add grid and legend
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=11, loc='upper right')
    
    # Tight layout
    plt.tight_layout()
    
    # Save the plot
    output_path = '../results/cohort_revenue_comparison_with_OS.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Saved plot: {output_path}")
    
    # Save cohort data as CSV
    csv_path = '../results/cohort_analysis_with_OS.csv'
    cohort_data.to_csv(csv_path, index=False)
    print(f"✅ Saved data: {csv_path}")
    
    # Show top and bottom performing cohorts
    print(f"\n🏆 TOP 10 COHORTS BY ACTUAL REVENUE:")
    print("-" * 50)
    top_cohorts = cohort_data.nlargest(10, 'total_actual_revenue')
    for _, row in top_cohorts.iterrows():
        accuracy = (row['total_predicted_revenue'] / row['total_actual_revenue']) * 100
        print(f"   {row['first_event_date'].strftime('%Y-%m-%d')}: "
              f"${row['total_actual_revenue']:7,.0f} actual, "
              f"${row['total_predicted_revenue']:7,.0f} predicted "
              f"({accuracy:5.1f}% accuracy)")
    
    print(f"\n📉 BOTTOM 10 COHORTS BY ACTUAL REVENUE:")
    print("-" * 50)
    bottom_cohorts = cohort_data.nsmallest(10, 'total_actual_revenue')
    for _, row in bottom_cohorts.iterrows():
        accuracy = (row['total_predicted_revenue'] / row['total_actual_revenue']) * 100 if row['total_actual_revenue'] > 0 else 0
        print(f"   {row['first_event_date'].strftime('%Y-%m-%d')}: "
              f"${row['total_actual_revenue']:7,.0f} actual, "
              f"${row['total_predicted_revenue']:7,.0f} predicted "
              f"({accuracy:5.1f}% accuracy)")
    
    # Model improvement analysis
    print(f"\n🔍 MODEL PERFORMANCE ANALYSIS:")
    print("-" * 50)
    
    # Calculate accuracy per cohort
    cohort_data['accuracy'] = (cohort_data['total_predicted_revenue'] / cohort_data['total_actual_revenue']) * 100
    
    print(f"   Mean Accuracy: {cohort_data['accuracy'].mean():.1f}%")
    print(f"   Median Accuracy: {cohort_data['accuracy'].median():.1f}%")
    print(f"   Std Accuracy: {cohort_data['accuracy'].std():.1f}%")
    print(f"   Cohorts within ±10%: {((cohort_data['accuracy'] >= 90) & (cohort_data['accuracy'] <= 110)).sum()}/{len(cohort_data)} ({((cohort_data['accuracy'] >= 90) & (cohort_data['accuracy'] <= 110)).mean()*100:.1f}%)")
    
    # Correlation between actual and predicted
    correlation = cohort_data['total_actual_revenue'].corr(cohort_data['total_predicted_revenue'])
    print(f"   Revenue Correlation: {correlation:.3f}")
    
    print(f"\n🎉 COHORT VISUALIZATION COMPLETED!")
    print("="*60)
    
    return cohort_data

if __name__ == "__main__":
    cohort_data = create_cohort_visualization()
    plt.show()
