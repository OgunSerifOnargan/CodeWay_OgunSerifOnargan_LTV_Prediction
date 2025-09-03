import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# Database connection
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def analyze_high_revenue_user_patterns():
    """
    Analyze the most common first 3 event patterns for users in the top revenue quantile
    """
    try:
        # Connect to database
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        print("🔍 Analyzing high-revenue user patterns...")
        
        # Step 1: Find Quantile 3 threshold for yearly_revenue
        print("📊 Step 1: Finding Quantile 3 threshold for yearly_revenue...")
        
        quantile_query = """
        SELECT 
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY first_year_revenue) as quantile_3_threshold,
            COUNT(*) as total_users,
            COUNT(CASE WHEN first_year_revenue IS NOT NULL THEN 1 END) as users_with_revenue,
            AVG(first_year_revenue) as avg_revenue,
            MIN(first_year_revenue) as min_revenue,
            MAX(first_year_revenue) as max_revenue
        FROM random_user_subset
        """
        
        cursor.execute(quantile_query)
        quantile_data = cursor.fetchone()
        
        quantile_3_threshold = quantile_data[0]
        total_users = quantile_data[1]
        users_with_revenue = quantile_data[2]
        avg_revenue = quantile_data[3]
        min_revenue = quantile_data[4]
        max_revenue = quantile_data[5]
        
        print(f"✅ Quantile 3 threshold: ${quantile_3_threshold:.2f}")
        print(f"📊 Total users: {total_users:,}")
        print(f"📊 Users with revenue: {users_with_revenue:,}")
        print(f"📊 Revenue range: ${min_revenue:.2f} to ${max_revenue:.2f}")
        print(f"📊 Average revenue: ${avg_revenue:.2f}")
        
        # Step 2: Find users above Quantile 3
        print("\n📊 Step 2: Finding users above Quantile 3...")
        
        high_revenue_users_query = """
        SELECT DISTINCT user_id, first_year_revenue
        FROM random_user_subset
        WHERE first_year_revenue >= %s
        ORDER BY first_year_revenue DESC
        """
        
        cursor.execute(high_revenue_users_query, (quantile_3_threshold,))
        high_revenue_users = cursor.fetchall()
        
        print(f"✅ Found {len(high_revenue_users):,} users above Quantile 3")
        
        if len(high_revenue_users) == 0:
            print("❌ No high-revenue users found!")
            return
        
        # Step 3: Create temporary table for high-revenue users
        print("📊 Step 3: Creating temporary table for high-revenue users...")
        
        cursor.execute("""
            CREATE TEMP TABLE temp_high_revenue_users AS
            SELECT DISTINCT user_id
            FROM random_user_subset
            WHERE first_year_revenue >= %s
        """, (quantile_3_threshold,))
        
        # Step 4: Extract first 3 event patterns for high-revenue users
        print("📊 Step 4: Extracting first 3 event patterns...")
        
        pattern_query = """
        WITH user_first_events AS (
            SELECT 
                user_id,
                event_name,
                event_time,
                ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time) as event_order
            FROM random_user_subset
            WHERE user_id IN (SELECT user_id FROM temp_high_revenue_users)
        ),
        filtered_events AS (
            SELECT *
            FROM user_first_events
            WHERE event_order <= 3
        )
        SELECT 
            user_id,
            STRING_AGG(event_name, ' → ' ORDER BY event_order) as pattern
        FROM filtered_events
        GROUP BY user_id
        ORDER BY user_id
        """
        
        cursor.execute(pattern_query)
        patterns = cursor.fetchall()
        
        print(f"✅ Extracted patterns for {len(patterns)} users")
        
        # Step 5: Count pattern frequencies
        print("📊 Step 5: Counting pattern frequencies...")
        
        pattern_counts = Counter([pattern[1] for pattern in patterns])
        
        # Get top 15 patterns
        top_patterns = pattern_counts.most_common(15)
        
        print("\n🏆 TOP 15 EVENT PATTERNS FOR HIGH-REVENUE USERS:")
        print("=" * 80)
        
        for i, (pattern, count) in enumerate(top_patterns, 1):
            percentage = (count / len(patterns)) * 100
            print(f"{i:2d}. {pattern}")
            print(f"    Count: {count} users ({percentage:.1f}%)")
            print()
        
        # Step 6: Create detailed analysis table
        print("📊 Step 6: Creating detailed analysis...")
        
        # Get more details about top patterns
        top_pattern_names = [pattern for pattern, _ in top_patterns[:5]]
        
        detailed_analysis = []
        for pattern in top_pattern_names:
            # Count users with this pattern
            cursor.execute("""
                WITH user_first_events AS (
                    SELECT 
                        user_id,
                        event_name,
                        event_time,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time) as event_order
                    FROM random_user_subset
                    WHERE user_id IN (SELECT user_id FROM temp_high_revenue_users)
                ),
                filtered_events AS (
                    SELECT *
                    FROM user_first_events
                    WHERE event_order <= 3
                ),
                user_patterns AS (
                    SELECT 
                        user_id,
                        STRING_AGG(event_name, ' → ' ORDER BY event_order) as pattern
                    FROM filtered_events
                    GROUP BY user_id
                )
                SELECT COUNT(DISTINCT user_id)
                FROM user_patterns
                WHERE pattern = %s
            """, (pattern,))
            
            user_count = cursor.fetchone()[0]
            
            # Get average revenue for users with this pattern
            cursor.execute("""
                WITH user_first_events AS (
                    SELECT 
                        user_id,
                        event_name,
                        event_time,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time) as event_order
                    FROM random_user_subset
                    WHERE user_id IN (SELECT user_id FROM temp_high_revenue_users)
                ),
                filtered_events AS (
                    SELECT *
                    FROM user_first_events
                    WHERE event_order <= 3
                ),
                user_patterns AS (
                    SELECT 
                        user_id,
                        STRING_AGG(event_name, ' → ' ORDER BY event_order) as pattern
                    FROM filtered_events
                    GROUP BY user_id
                ),
                pattern_users AS (
                    SELECT user_id
                    FROM user_patterns
                    WHERE pattern = %s
                )
                SELECT 
                    AVG(first_year_revenue) as avg_revenue,
                    MIN(first_year_revenue) as min_revenue,
                    MAX(first_year_revenue) as max_revenue,
                    COUNT(*) as total_events
                FROM random_user_subset r
                INNER JOIN pattern_users p ON r.user_id = p.user_id
            """, (pattern,))
            
            revenue_data = cursor.fetchone()
            avg_revenue = revenue_data[0] or 0
            min_revenue = revenue_data[1] or 0
            max_revenue = revenue_data[2] or 0
            total_events = revenue_data[3] or 0
            
            # Get average days active for users with this pattern
            cursor.execute("""
                WITH user_first_events AS (
                    SELECT 
                        user_id,
                        event_name,
                        event_time,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time) as event_order
                    FROM random_user_subset
                    WHERE user_id IN (SELECT user_id FROM temp_high_revenue_users)
                ),
                filtered_events AS (
                    SELECT *
                    FROM user_first_events
                    WHERE event_order <= 3
                ),
                user_patterns AS (
                    SELECT 
                        user_id,
                        STRING_AGG(event_name, ' → ' ORDER BY event_order) as pattern
                    FROM filtered_events
                    GROUP BY user_id
                ),
                pattern_users AS (
                    SELECT user_id
                    FROM user_patterns
                    WHERE pattern = %s
                )
                SELECT AVG(days_active)
                FROM (
                    SELECT 
                        r.user_id,
                        MAX(r.days_since_first_event) as days_active
                    FROM random_user_subset r
                    INNER JOIN pattern_users p ON r.user_id = p.user_id
                    GROUP BY r.user_id
                ) user_days_active
            """, (pattern,))
            
            avg_days_active = cursor.fetchone()[0] or 0
            
            detailed_analysis.append({
                'pattern': pattern,
                'user_count': user_count,
                'percentage': (user_count / len(patterns)) * 100,
                'avg_revenue': round(avg_revenue, 2),
                'min_revenue': round(min_revenue, 2),
                'max_revenue': round(max_revenue, 2),
                'total_events': total_events,
                'avg_days_active': round(avg_days_active, 1)
            })
        
        # Create detailed analysis table
        print("\n📋 DETAILED ANALYSIS OF TOP 5 PATTERNS:")
        print("=" * 80)
        
        df_analysis = pd.DataFrame(detailed_analysis)
        print(df_analysis.to_string(index=False))
        
        # Step 7: Create visualization
        print("\n📊 Step 7: Creating visualizations...")
        
        # Create pattern frequency chart
        plt.figure(figsize=(16, 10))
        
        # Top 10 patterns
        patterns, counts = zip(*top_patterns[:10])
        
        # Truncate long pattern names for display
        display_patterns = []
        for pattern in patterns:
            if len(pattern) > 60:
                display_patterns.append(pattern[:57] + "...")
            else:
                display_patterns.append(pattern)
        
        bars = plt.barh(range(len(display_patterns)), counts, color='#4ECDC4')
        plt.yticks(range(len(display_patterns)), display_patterns)
        plt.xlabel('Number of Users')
        plt.title('Top 10 Event Patterns for High-Revenue Users\n(First 3 Events, Above Quantile 3)', fontsize=14, fontweight='bold')
        
        # Add value labels on bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            percentage = (count / len(patterns)) * 100
            plt.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                    f'{count} ({percentage:.1f}%)', 
                    va='center', fontsize=10)
        
        plt.tight_layout()
        plt.savefig('high_revenue_user_patterns.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # Step 8: Save results to CSV
        print("\n💾 Step 8: Saving results...")
        
        # Save top patterns
        df_top_patterns = pd.DataFrame(top_patterns, columns=['Pattern', 'User_Count'])
        df_top_patterns['Percentage'] = df_top_patterns['User_Count'] / len(patterns) * 100
        df_top_patterns['Percentage'] = df_top_patterns['Percentage'].round(2)
        df_top_patterns.to_csv('high_revenue_user_patterns.csv', index=False)
        
        # Save detailed analysis
        df_analysis.to_csv('high_revenue_user_detailed_analysis.csv', index=False)
        
        print("✅ Results saved to:")
        print("   - high_revenue_user_patterns.csv")
        print("   - high_revenue_user_detailed_analysis.csv")
        print("   - high_revenue_user_patterns.png")
        
        # Step 9: Summary insights
        print("\n🎯 KEY INSIGHTS:")
        print("=" * 80)
        
        print(f"📊 High-revenue users (above Q3): {len(high_revenue_users):,} out of {total_users:,} total users")
        print(f"📊 Revenue threshold: ${quantile_3_threshold:.2f}")
        
        if detailed_analysis:
            top_pattern = detailed_analysis[0]
            print(f"🏆 Most common pattern: '{top_pattern['pattern']}'")
            print(f"   - Used by {top_pattern['user_count']} users ({top_pattern['percentage']:.1f}% of high-revenue users)")
            print(f"   - Average revenue: ${top_pattern['avg_revenue']}")
            print(f"   - Revenue range: ${top_pattern['min_revenue']} to ${top_pattern['max_revenue']}")
            print(f"   - Average days active: {top_pattern['avg_days_active']}")
        
        # Step 10: Business insights
        print("\n💡 BUSINESS INSIGHTS:")
        print("=" * 80)
        
        # Find patterns with high conversion potential
        high_conversion_patterns = []
        for pattern_data in detailed_analysis[:3]:
            if pattern_data['percentage'] > 10:  # More than 10% of high-revenue users
                high_conversion_patterns.append(pattern_data)
        
        if high_conversion_patterns:
            print("🎯 HIGH-CONVERSION PATTERNS (Target for marketing):")
            for pattern_data in high_conversion_patterns:
                print(f"   - '{pattern_data['pattern']}': {pattern_data['percentage']:.1f}% of high-revenue users")
                print(f"     → Average revenue: ${pattern_data['avg_revenue']}")
                print(f"     → User count: {pattern_data['user_count']}")
                print()
        
        # Clean up temporary table
        cursor.execute("DROP TABLE temp_high_revenue_users")
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("\n✅ Analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    analyze_high_revenue_user_patterns()
