import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

# Database connection
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def analyze_15_day_revenue_timeline():
    """Analyze 15-day revenue timeline using random_user_subset with days_since_first_event"""
    print("📊 ANALYZING 15-DAY REVENUE TIMELINE")
    print("=" * 50)
    
    engine = create_engine(DB_URL)
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        print("📊 Loading daily revenue data from random_user_subset...")
        
        # Get daily revenue data using the days_since_first_event column
        query = """
        SELECT 
            days_since_first_event,
            COUNT(*) as event_count,
            COUNT(DISTINCT user_id) as unique_users,
            SUM(COALESCE(first_year_revenue, 0)) as total_revenue,
            AVG(COALESCE(first_year_revenue, 0)) as avg_revenue_per_event,
            AVG(COALESCE(first_year_revenue, 0)) as avg_revenue_per_user
        FROM random_user_subset
        WHERE days_since_first_event IS NOT NULL
        AND days_since_first_event BETWEEN 0 AND 14
        GROUP BY days_since_first_event
        ORDER BY days_since_first_event
        """
        
        df = pd.read_sql(query, engine)
        print(f"📊 Loaded daily revenue data for {len(df):,} days")
        
        # Fill missing days with 0
        all_days = pd.DataFrame({'days_since_first_event': range(15)})
        df = all_days.merge(df, on='days_since_first_event', how='left').fillna(0)
        
        # Create the visualization
        print("🎨 Creating visualization...")
        
        # Set style
        plt.style.use('seaborn-v0_8')
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        days = df['days_since_first_event'].values
        event_counts = df['event_count'].values
        unique_users = df['unique_users'].values
        daily_revenue_sums = df['total_revenue'].values
        daily_revenue_means = df['avg_revenue_per_event'].values
        
        # Plot 1: Daily Event Count
        ax1.bar(days, event_counts, color='lightblue', alpha=0.7, edgecolor='navy')
        ax1.set_title('📊 15-Day Timeline: Daily Event Count', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Days Since First Event', fontsize=12)
        ax1.set_ylabel('Number of Events', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(event_counts):
            ax1.text(i, v + max(event_counts)*0.01, f'{v:,.0f}', 
                    ha='center', va='bottom', fontweight='bold')
        
        # Plot 2: Daily Total Revenue
        ax2.bar(days, daily_revenue_sums, color='lightgreen', alpha=0.7, edgecolor='darkgreen')
        ax2.set_title('💰 15-Day Timeline: Daily Total Revenue', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Days Since First Event', fontsize=12)
        ax2.set_ylabel('Total Revenue ($)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(daily_revenue_sums):
            ax2.text(i, v + max(daily_revenue_sums)*0.01, f'${v:,.0f}', 
                    ha='center', va='bottom', fontweight='bold')
        
        # Plot 3: Daily Average Revenue per Event
        ax3.plot(days, daily_revenue_means, marker='o', linewidth=3, markersize=8, 
                color='orange', markerfacecolor='lightcoral', markeredgecolor='darkorange')
        ax3.fill_between(days, daily_revenue_means, alpha=0.3, color='lightcoral')
        ax3.set_title('📈 15-Day Timeline: Daily Average Revenue per Event', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Days Since First Event', fontsize=12)
        ax3.set_ylabel('Average Revenue per Event ($)', fontsize=12)
        ax3.grid(True, alpha=0.3)
        
        # Add value labels on points
        for i, v in enumerate(daily_revenue_means):
            ax3.text(i, v + max(daily_revenue_means)*0.01, f'${v:.2f}', 
                    ha='center', va='bottom', fontweight='bold')
        
        # Plot 4: Unique Users per Day
        ax4.bar(days, unique_users, color='lightcoral', alpha=0.7, edgecolor='darkred')
        ax4.set_title('👥 15-Day Timeline: Unique Users per Day', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Days Since First Event', fontsize=12)
        ax4.set_ylabel('Number of Unique Users', fontsize=12)
        ax4.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(unique_users):
            ax4.text(i, v + max(unique_users)*0.01, f'{v:,.0f}', 
                    ha='center', va='bottom', fontweight='bold')
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        plt.savefig('15_day_revenue_timeline.png', dpi=300, bbox_inches='tight')
        print("💾 Plot saved as '15_day_revenue_timeline.png'")
        
        # Show the plot
        plt.show()
        
        # Print summary statistics
        print("\n📋 15-DAY REVENUE TIMELINE SUMMARY:")
        print("=" * 70)
        print(f"{'Day':<4} {'Events':<10} {'Users':<10} {'Total Rev':<15} {'Avg Rev/Event':<18}")
        print("-" * 70)
        
        for i, day in enumerate(days):
            events = event_counts[i]
            users = unique_users[i]
            total_rev = daily_revenue_sums[i]
            avg_rev = daily_revenue_means[i]
            print(f"{day:<4} {events:<10,} {users:<10,} ${total_rev:<14,.0f} ${avg_rev:<17,.2f}")
        
        # Additional insights
        print(f"\n💡 INSIGHTS:")
        print(f"  • Total 15-day events: {sum(event_counts):,}")
        print(f"  • Total 15-day revenue: ${sum(daily_revenue_sums):,.2f}")
        print(f"  • Peak event day: Day {np.argmax(event_counts)} ({max(event_counts):,} events)")
        print(f"  • Peak revenue day: Day {np.argmax(daily_revenue_sums)} (${max(daily_revenue_sums):,.2f})")
        print(f"  • Average events per day: {np.mean(event_counts):.1f}")
        print(f"  • Average revenue per day: ${np.mean(daily_revenue_sums):,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 15-DAY REVENUE TIMELINE ANALYSIS")
    print("=" * 50)
    
    # Run the analysis
    success = analyze_15_day_revenue_timeline()
    
    if success:
        print("\n🎉 Timeline analysis completed!")
        print("💡 You can now see:")
        print("   - Daily event counts")
        print("   - Daily revenue totals")
        print("   - User engagement patterns")
        print("   - Revenue distribution over 15 days")
    else:
        print("\n❌ Failed to complete timeline analysis")
