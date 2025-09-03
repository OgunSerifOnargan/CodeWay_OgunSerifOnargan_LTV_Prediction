import pandas as pd
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

# Database connection
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def analyze_paywall_revenue():
    """Analyze if revenue is generated from paywall events"""
    print("💰 ANALYZING PAYWALL REVENUE")
    print("=" * 50)
    
    engine = create_engine(DB_URL)
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        print("🔍 Checking paywall events and revenue correlation...")
        
        # Check if paywall events exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    event_name,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM raw_dataset 
                WHERE event_name LIKE '%paywall%'
                GROUP BY event_name
                ORDER BY event_count DESC
            """))
            paywall_events = result.fetchall()
            
            print("📊 PAYWALL EVENTS FOUND:")
            for event in paywall_events:
                print(f"  {event[0]}: {event[1]:,} events, {event[2]:,} unique users")
        
        # Check if paywall events have revenue
        print("\n💰 CHECKING PAYWALL REVENUE:")
        with engine.connect() as conn:
            # Check direct revenue from paywall events
            result = conn.execute(text("""
                SELECT 
                    event_name,
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN first_year_revenue > 0 THEN 1 END) as events_with_revenue,
                    COUNT(CASE WHEN first_year_revenue IS NULL THEN 1 END) as events_without_revenue,
                    AVG(COALESCE(first_year_revenue, 0)) as avg_revenue,
                    SUM(COALESCE(first_year_revenue, 0)) as total_revenue
                FROM raw_dataset 
                WHERE event_name LIKE '%paywall%'
                GROUP BY event_name
                ORDER BY total_revenue DESC
            """))
            paywall_revenue = result.fetchall()
            
            for event in paywall_revenue:
                print(f"\n  {event[0]}:")
                print(f"    Total events: {event[1]:,}")
                print(f"    Events with revenue: {event[2]:,}")
                print(f"    Events without revenue: {event[3]:,}")
                print(f"    Average revenue: ${event[4]:.2f}")
                print(f"    Total revenue: ${event[5]:.2f}")
        
        # Check revenue timing around paywall events
        print("\n⏰ REVENUE TIMING AROUND PAYWALL EVENTS:")
        with engine.connect() as conn:
            result = conn.execute(text("""
                WITH paywall_users AS (
                    SELECT DISTINCT user_id
                    FROM raw_dataset 
                    WHERE event_name LIKE '%paywall%'
                ),
                user_revenue_timing AS (
                    SELECT 
                        pu.user_id,
                        rd.event_name,
                        rd.event_time,
                        rd.first_year_revenue,
                        CASE 
                            WHEN rd.first_year_revenue > 0 THEN 'HAS_REVENUE'
                            ELSE 'NO_REVENUE'
                        END as revenue_status
                    FROM paywall_users pu
                    INNER JOIN raw_dataset rd ON pu.user_id = rd.user_id
                    WHERE rd.event_name IN ('paywall', 'subscription_started', 'subscription_renewed')
                    ORDER BY pu.user_id, rd.event_time
                )
                SELECT 
                    revenue_status,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(COALESCE(first_year_revenue, 0)) as avg_revenue
                FROM user_revenue_timing
                GROUP BY revenue_status
                ORDER BY avg_revenue DESC
            """))
            revenue_timing = result.fetchall()
            
            for timing in revenue_timing:
                print(f"  {timing[0]}: {timing[1]:,} users, avg revenue: ${timing[2]:.2f}")
        
        # Check if paywall is a conversion funnel step
        print("\n🔄 PAYWALL AS CONVERSION FUNNEL STEP:")
        with engine.connect() as conn:
            result = conn.execute(text("""
                WITH user_journey AS (
                    SELECT 
                        user_id,
                        event_name,
                        event_time,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time) as step_order
                    FROM raw_dataset 
                    WHERE user_id IN (
                        SELECT DISTINCT user_id 
                        FROM raw_dataset 
                        WHERE event_name LIKE '%paywall%'
                    )
                    AND event_name IN ('paywall', 'subscription_started', 'subscription_renewed', 'free_trial')
                    ORDER BY user_id, event_time
                ),
                conversion_paths AS (
                    SELECT 
                        user_id,
                        STRING_AGG(event_name, ' → ' ORDER BY step_order) as conversion_path
                    FROM user_journey
                    GROUP BY user_id
                )
                SELECT 
                    conversion_path,
                    COUNT(*) as user_count
                FROM conversion_paths
                GROUP BY conversion_path
                ORDER BY user_count DESC
                LIMIT 10
            """))
            conversion_paths = result.fetchall()
            
            print("  Top conversion paths involving paywall:")
            for path in conversion_paths:
                print(f"    {path[0]}: {path[1]:,} users")
        
        # Summary
        print("\n📋 SUMMARY:")
        with engine.connect() as conn:
            # Total paywall events
            result = conn.execute(text("""
                SELECT COUNT(*) as total_paywall_events
                FROM raw_dataset 
                WHERE event_name LIKE '%paywall%'
            """))
            total_paywall = result.scalar()
            
            # Users who saw paywall
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT user_id) as users_with_paywall
                FROM raw_dataset 
                WHERE event_name LIKE '%paywall%'
            """))
            users_with_paywall = result.scalar()
            
            # Users with paywall who converted
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT rd1.user_id) as paywall_users_converted
                FROM raw_dataset rd1
                INNER JOIN raw_dataset rd2 ON rd1.user_id = rd2.user_id
                WHERE rd1.event_name LIKE '%paywall%'
                AND rd2.event_name IN ('subscription_started', 'subscription_renewed')
            """))
            paywall_converted = result.scalar()
            
            # Revenue from paywall users
            result = conn.execute(text("""
                SELECT 
                    SUM(COALESCE(first_year_revenue, 0)) as total_revenue_from_paywall_users
                FROM raw_dataset 
                WHERE user_id IN (
                    SELECT DISTINCT user_id 
                    FROM raw_dataset 
                    WHERE event_name LIKE '%paywall%'
                )
                AND first_year_revenue > 0
            """))
            total_revenue = result.scalar()
            
            print(f"  Total paywall events: {total_paywall:,}")
            print(f"  Users who saw paywall: {users_with_paywall:,}")
            print(f"  Paywall users who converted: {paywall_converted:,}")
            print(f"  Conversion rate: {paywall_converted/users_with_paywall*100:.1f}%")
            print(f"  Total revenue from paywall users: ${total_revenue:,.2f}")
            
            if total_revenue > 0:
                print("  ✅ PAYWALL IS GENERATING REVENUE!")
            else:
                print("  ❌ PAYWALL IS NOT GENERATING DIRECT REVENUE")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 PAYWALL REVENUE ANALYSIS")
    print("=" * 50)
    
    # Run the analysis
    success = analyze_paywall_revenue()
    
    if success:
        print("\n🎉 Analysis completed!")
    else:
        print("\n❌ Failed to complete paywall revenue analysis")
