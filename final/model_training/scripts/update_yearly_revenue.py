import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def update_actual_yearly_revenue():
    """Update test_predictions table with actual yearly revenue using vectorized pandas"""
    
    print("🚀 UPDATING ACTUAL YEARLY REVENUE...")
    print("="*60)
    
    engine = create_engine(DB_URL)
    
    # Step 1: Load user-level first_year_revenue from raw_dataset
    print("📥 Loading user-level first_year_revenue from raw_dataset...")
    raw_query = """
    SELECT 
        user_id,
        MAX(first_year_revenue) as actual_yearly_revenue
    FROM raw_dataset
    GROUP BY user_id
    """
    
    user_revenue_df = pd.read_sql(raw_query, engine)
    print(f"   ✅ Loaded {len(user_revenue_df):,} users from raw_dataset")
    print(f"   📊 Revenue stats: Mean=${user_revenue_df['actual_yearly_revenue'].mean():.2f}, Max=${user_revenue_df['actual_yearly_revenue'].max():.2f}")
    
    # Step 2: Load current test_predictions
    print("\n📥 Loading current test_predictions...")
    test_pred_query = "SELECT user_id, actual_ltv FROM test_predictions"
    test_df = pd.read_sql(test_pred_query, engine)
    print(f"   ✅ Loaded {len(test_df):,} users from test_predictions")
    
    # Step 3: Merge to get yearly revenue for test users (vectorized operation)
    print("\n🔗 Merging data using vectorized pandas operations...")
    merged_df = test_df.merge(user_revenue_df, on='user_id', how='left')
    
    # Fill any missing values with 0 (shouldn't happen but just in case)
    merged_df['actual_yearly_revenue'] = merged_df['actual_yearly_revenue'].fillna(0)
    
    print(f"   ✅ Merged successfully: {len(merged_df):,} users")
    print(f"   📊 Yearly revenue stats for test users:")
    print(f"      Mean: ${merged_df['actual_yearly_revenue'].mean():.2f}")
    print(f"      Median: ${merged_df['actual_yearly_revenue'].median():.2f}")
    print(f"      Max: ${merged_df['actual_yearly_revenue'].max():.2f}")
    print(f"      Non-zero users: {(merged_df['actual_yearly_revenue'] > 0).sum():,} ({(merged_df['actual_yearly_revenue'] > 0).mean()*100:.1f}%)")
    
    # Step 4: Verify consistency with actual_ltv
    print("\n🔍 Verifying consistency with actual_ltv...")
    consistent_users = (merged_df['actual_ltv'] == merged_df['actual_yearly_revenue']).sum()
    total_users = len(merged_df)
    consistency_rate = consistent_users / total_users * 100
    
    print(f"   Consistent users: {consistent_users:,}/{total_users:,} ({consistency_rate:.1f}%)")
    
    if consistency_rate < 100:
        print("   ⚠️  Some inconsistencies found - this is expected if actual_ltv and yearly_revenue are different metrics")
        
        # Show some examples of differences
        diff_users = merged_df[merged_df['actual_ltv'] != merged_df['actual_yearly_revenue']].head(5)
        if len(diff_users) > 0:
            print("   📊 Sample differences:")
            for _, row in diff_users.iterrows():
                print(f"      User {row['user_id']}: actual_ltv=${row['actual_ltv']:.2f}, yearly_revenue=${row['actual_yearly_revenue']:.2f}")
    
    # Step 5: Update test_predictions table using vectorized approach
    print(f"\n💾 Updating test_predictions table...")
    
    # Create a temporary table for efficient update
    temp_table_name = "temp_yearly_revenue_update"
    
    # Drop temp table if exists
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {temp_table_name}"))
        conn.commit()
    
    # Save update data to temporary table
    update_df = merged_df[['user_id', 'actual_yearly_revenue']]
    update_df.to_sql(temp_table_name, engine, index=False, if_exists='replace', method='multi')
    
    print(f"   ✅ Created temporary table with {len(update_df):,} records")
    
    # Perform vectorized update using JOIN
    update_query = f"""
    UPDATE test_predictions 
    SET actual_yearly_revenue = temp.actual_yearly_revenue
    FROM {temp_table_name} temp
    WHERE test_predictions.user_id = temp.user_id
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(update_query))
        conn.commit()
        print(f"   ✅ Updated {result.rowcount:,} records in test_predictions")
    
    # Clean up temporary table
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE {temp_table_name}"))
        conn.commit()
    
    print("   ✅ Cleaned up temporary table")
    
    # Step 6: Verify the update
    print(f"\n🔍 Verifying update...")
    verification_query = """
    SELECT 
        COUNT(*) as total_records,
        COUNT(actual_yearly_revenue) as records_with_yearly_revenue,
        AVG(actual_yearly_revenue) as avg_yearly_revenue,
        MAX(actual_yearly_revenue) as max_yearly_revenue,
        SUM(CASE WHEN actual_yearly_revenue > 0 THEN 1 ELSE 0 END) as paying_users
    FROM test_predictions
    """
    
    verification_df = pd.read_sql(verification_query, engine)
    stats = verification_df.iloc[0]
    
    print(f"   Total records: {int(stats['total_records']):,}")
    print(f"   Records with yearly revenue: {int(stats['records_with_yearly_revenue']):,}")
    print(f"   Average yearly revenue: ${stats['avg_yearly_revenue']:.2f}")
    print(f"   Max yearly revenue: ${stats['max_yearly_revenue']:.2f}")
    print(f"   Paying users: {int(stats['paying_users']):,}")
    
    # Step 7: Show sample results
    print(f"\n📊 Sample results:")
    sample_query = """
    SELECT user_id, actual_ltv, actual_yearly_revenue,
           CASE WHEN actual_ltv = actual_yearly_revenue THEN 'MATCH' ELSE 'DIFFERENT' END as comparison
    FROM test_predictions 
    WHERE actual_yearly_revenue > 0
    ORDER BY actual_yearly_revenue DESC 
    LIMIT 10
    """
    
    sample_df = pd.read_sql(sample_query, engine)
    for _, row in sample_df.iterrows():
        print(f"   {row['user_id']}: LTV=${row['actual_ltv']:.2f}, Yearly=${row['actual_yearly_revenue']:.2f} ({row['comparison']})")
    
    print(f"\n🎉 ACTUAL YEARLY REVENUE UPDATE COMPLETED!")
    print("="*60)
    
    return merged_df

if __name__ == "__main__":
    result_df = update_actual_yearly_revenue()
