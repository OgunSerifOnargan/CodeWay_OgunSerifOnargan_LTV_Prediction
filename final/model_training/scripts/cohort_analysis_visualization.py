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

def create_cohort_revenue_analysis():
    """Create cohort-level revenue analysis and visualization"""
    
    print("📊 CREATING COHORT REVENUE ANALYSIS...")
    print("="*60)
    
    engine = create_engine(DB_URL)
    
    # Load test predictions from database
    print("📥 Loading test predictions from database...")
    query = """
    SELECT 
        first_event_date,
        actual_ltv,
        predicted_ltv,
        user_id
    FROM test_predictions
    ORDER BY first_event_date
    """
    
    df = pd.read_sql(query, engine)
    print(f"   ✅ Loaded {len(df):,} predictions")
    
    # Convert first_event_date to datetime
    df['first_event_date'] = pd.to_datetime(df['first_event_date'])
    
    # Group by cohort (first_event_date) and calculate totals
    print("🔄 Grouping by cohorts and calculating revenue totals...")
    cohort_analysis = df.groupby('first_event_date').agg({
        'user_id': 'count',
        'actual_ltv': 'sum',
        'predicted_ltv': 'sum'
    }).reset_index()
    
    # Rename columns for clarity
    cohort_analysis.columns = ['cohort_date', 'user_count', 'actual_revenue', 'predicted_revenue']
    
    # Calculate accuracy for each cohort
    cohort_analysis['revenue_accuracy'] = (cohort_analysis['predicted_revenue'] / cohort_analysis['actual_revenue'] * 100).round(1)
    
    # Sort by date
    cohort_analysis = cohort_analysis.sort_values('cohort_date')
    
    print(f"   ✅ Analyzed {len(cohort_analysis)} cohorts")
    print(f"   📅 Date range: {cohort_analysis['cohort_date'].min().strftime('%Y-%m-%d')} to {cohort_analysis['cohort_date'].max().strftime('%Y-%m-%d')}")
    
    # Display top cohorts by actual revenue
    print("\n🏆 TOP 10 COHORTS BY ACTUAL REVENUE:")
    top_cohorts = cohort_analysis.nlargest(10, 'actual_revenue')
    for _, row in top_cohorts.iterrows():
        print(f"   {row['cohort_date'].strftime('%Y-%m-%d')}: ${row['actual_revenue']:,.2f} actual, ${row['predicted_revenue']:,.2f} predicted ({row['revenue_accuracy']:.1f}% accuracy)")
    
    # Create visualization
    print("\n📈 Creating cohort revenue visualization...")
    
    # Set up the plot style
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # Plot actual and predicted revenue lines
    ax.plot(cohort_analysis['cohort_date'], cohort_analysis['actual_revenue'], 
            linewidth=2.5, color='#1f77b4', marker='o', markersize=4, 
            label='Actual Revenue', alpha=0.8)
    
    ax.plot(cohort_analysis['cohort_date'], cohort_analysis['predicted_revenue'], 
            linewidth=2.5, color='#ff7f0e', marker='s', markersize=4, 
            label='Predicted Revenue', alpha=0.8)
    
    # Customize the plot
    ax.set_xlabel('Cohort Date (First Event Date)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Revenue ($)', fontsize=12, fontweight='bold')
    ax.set_title('Cohort-Level Revenue Analysis: Actual vs Predicted\nLTV Prediction Model Performance by User Acquisition Date', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Format y-axis to show currency
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
    
    # Add summary statistics as text box
    total_actual = cohort_analysis['actual_revenue'].sum()
    total_predicted = cohort_analysis['predicted_revenue'].sum()
    overall_accuracy = (total_predicted / total_actual * 100)
    
    stats_text = f"""Overall Performance:
Total Actual: ${total_actual:,.0f}
Total Predicted: ${total_predicted:,.0f}
Revenue Accuracy: {overall_accuracy:.1f}%
Cohorts Analyzed: {len(cohort_analysis)}"""
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_filename = f"../results/cohort_revenue_analysis_{timestamp}.png"
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight', facecolor='white')
    
    print(f"   ✅ Plot saved: {plot_filename}")
    
    # Display the plot
    plt.show()
    
    # Save cohort analysis data
    csv_filename = f"../results/cohort_analysis_data_{timestamp}.csv"
    cohort_analysis.to_csv(csv_filename, index=False)
    print(f"   ✅ Data saved: {csv_filename}")
    
    # Print detailed statistics
    print(f"\n📊 COHORT ANALYSIS SUMMARY:")
    print("="*50)
    print(f"Total Cohorts: {len(cohort_analysis)}")
    print(f"Total Users: {cohort_analysis['user_count'].sum():,}")
    print(f"Total Actual Revenue: ${total_actual:,.2f}")
    print(f"Total Predicted Revenue: ${total_predicted:,.2f}")
    print(f"Overall Revenue Accuracy: {overall_accuracy:.1f}%")
    print(f"Average Users per Cohort: {cohort_analysis['user_count'].mean():.0f}")
    print(f"Average Actual Revenue per Cohort: ${cohort_analysis['actual_revenue'].mean():,.2f}")
    print(f"Average Predicted Revenue per Cohort: ${cohort_analysis['predicted_revenue'].mean():,.2f}")
    
    # Accuracy distribution
    accuracy_stats = cohort_analysis['revenue_accuracy'].describe()
    print(f"\n🎯 ACCURACY DISTRIBUTION:")
    print(f"Mean Accuracy: {accuracy_stats['mean']:.1f}%")
    print(f"Median Accuracy: {accuracy_stats['50%']:.1f}%")
    print(f"Min Accuracy: {accuracy_stats['min']:.1f}%")
    print(f"Max Accuracy: {accuracy_stats['max']:.1f}%")
    print(f"Std Accuracy: {accuracy_stats['std']:.1f}%")
    
    return cohort_analysis

if __name__ == "__main__":
    cohort_data = create_cohort_revenue_analysis()
