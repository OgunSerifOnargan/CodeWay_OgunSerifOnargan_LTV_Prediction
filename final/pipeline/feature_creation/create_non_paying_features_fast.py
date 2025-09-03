import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def create_non_paying_features_fast():
    """
    Non-paying users'ı ayırt edecek feature'ları hızlı şekilde oluşturur
    Pandas vektörize operations kullanarak maximum speed sağlar
    """
    
    print("🚀 CREATING NON-PAYING USER FEATURES (FAST VERSION)")
    print("="*60)
    
    engine = create_engine(DB_URL)
    
    # 1. Raw data'yı chunk'lar halinde oku
    print("📊 Loading raw dataset in chunks...")
    
    # İlk olarak user'ların first_event_date bilgisini alalım (daha küçük sample ile test)
    user_dates_query = """
    SELECT user_id, first_event_date, first_year_revenue
    FROM raw_dataset
    GROUP BY user_id, first_event_date, first_year_revenue
    LIMIT 10000
    """
    
    user_dates = pd.read_sql(user_dates_query, engine)
    print(f"   ✅ Loaded {len(user_dates):,} users")
    
    # 2. Chunk'lar halinde process et (çok daha küçük chunk)
    chunk_size = 1000
    all_features = []
    
    print(f"🔄 Processing users in chunks of {chunk_size:,}...")
    
    for i in tqdm(range(0, len(user_dates), chunk_size), desc="Processing chunks"):
        chunk_users = user_dates.iloc[i:i+chunk_size]
        user_ids = chunk_users['user_id'].tolist()
        
        # User ID'leri SQL için hazırla
        user_ids_str = ','.join([f"'{uid}'" for uid in user_ids])
        
        # Bu chunk için event data'sını çek
        chunk_query = f"""
        WITH user_15day_windows AS (
            SELECT 
                user_id,
                first_event_date::date as first_event_date,
                first_event_date::date + INTERVAL '15 days' as end_date
            FROM raw_dataset
            WHERE user_id IN ({user_ids_str})
            GROUP BY user_id, first_event_date
        ),
        filtered_events AS (
            SELECT 
                r.user_id,
                r.event_name,
                r.event_date::date as event_date,
                r.revenue,
                w.first_event_date
            FROM raw_dataset r
            JOIN user_15day_windows w ON r.user_id = w.user_id
            WHERE r.event_date::date >= w.first_event_date 
            AND r.event_date::date <= w.end_date
        )
        SELECT 
            user_id,
            event_name,
            event_date,
            revenue,
            first_event_date
        FROM filtered_events
        ORDER BY user_id, event_date
        """
        
        chunk_events = pd.read_sql(chunk_query, engine)
        
        if len(chunk_events) == 0:
            continue
            
        # 3. Pandas vektörize operations ile feature'ları hesapla
        chunk_features = calculate_features_vectorized(chunk_events)
        
        # Target variable'ı ekle
        chunk_features = chunk_features.merge(
            chunk_users[['user_id', 'first_year_revenue']], 
            on='user_id', 
            how='left'
        )
        
        all_features.append(chunk_features)
    
    # 4. Tüm chunk'ları birleştir
    print("🔗 Combining all chunks...")
    final_features = pd.concat(all_features, ignore_index=True)
    
    print(f"   ✅ Created features for {len(final_features):,} users")
    
    # 5. Database'e kaydet
    save_to_database(final_features, engine)
    
    # 6. Analysis yap
    analyze_features(final_features)
    
    print(f"\n🎉 NON-PAYING FEATURES COMPLETED!")
    print("="*60)
    
    return final_features

def calculate_features_vectorized(events_df):
    """
    Pandas vektörize operations ile feature'ları hesaplar
    """
    
    print("   🧮 Calculating features with vectorized operations...")
    
    # Group by user_id for aggregations
    user_groups = events_df.groupby('user_id')
    
    features = []
    
    for user_id, user_events in user_groups:
        first_event_date = user_events['first_event_date'].iloc[0]
        
        # Convert to datetime for calculations
        user_events_copy = user_events.copy()
        user_events_copy['event_date'] = pd.to_datetime(user_events_copy['event_date'])
        first_date = pd.to_datetime(first_event_date)
        
        # Calculate all features vectorized
        feature_dict = {
            'user_id': user_id,
            
            # 1. BINARY FEATURES
            'is_single_day_user': int(user_events_copy['event_date'].dt.date.nunique() == 1),
            
            'has_immediate_paywall_bounce': int(
                (user_events_copy['event_name'] == 'paywall').any() and
                len(user_events_copy) <= 2 and
                user_events_copy['event_date'].dt.date.nunique() == 1
            ),
            
            'has_paywall_no_conversion': int(
                (user_events_copy['event_name'] == 'paywall').sum() > 5 and
                (user_events_copy['event_name'] == 'subscribe').sum() == 0
            ),
            
            'has_no_trial_usage': int((user_events_copy['event_name'] == 'free_trial').sum() == 0),
            
            # 2. COUNT FEATURES
            'total_events_15d': len(user_events_copy),
            'active_days_15d': user_events_copy['event_date'].dt.date.nunique(),
            
            # 3. RATIO FEATURES
            'paywall_event_ratio': (user_events_copy['event_name'] == 'paywall').sum() / len(user_events_copy) if len(user_events_copy) > 0 else 0,
        }
        
        # 4. EARLY ACTIVITY CONCENTRATION
        early_period = first_date + pd.Timedelta(days=3)
        early_events = user_events_copy[user_events_copy['event_date'] < early_period]
        feature_dict['early_activity_ratio'] = len(early_events) / len(user_events_copy) if len(user_events_copy) > 0 else 0
        
        # 5. ENGAGEMENT DEPTH CATEGORY
        unique_events = user_events_copy['event_name'].nunique()
        has_subscribe = (user_events_copy['event_name'] == 'subscribe').any()
        has_trial = (user_events_copy['event_name'] == 'free_trial').any()
        
        if unique_events >= 4 and has_subscribe:
            feature_dict['engagement_depth'] = 'Deep'
        elif unique_events >= 3 or has_trial:
            feature_dict['engagement_depth'] = 'Medium'
        elif unique_events >= 2 and len(user_events_copy) >= 5:
            feature_dict['engagement_depth'] = 'Shallow'
        else:
            feature_dict['engagement_depth'] = 'Surface'
        
        # 6. PROGRESSION FUNNEL STAGE
        has_renewal = (user_events_copy['event_name'] == 'renewal').any()
        has_paywall = (user_events_copy['event_name'] == 'paywall').any()
        
        if has_renewal:
            feature_dict['funnel_stage'] = 4
        elif has_subscribe:
            feature_dict['funnel_stage'] = 3
        elif has_trial:
            feature_dict['funnel_stage'] = 2
        elif has_paywall:
            feature_dict['funnel_stage'] = 1
        else:
            feature_dict['funnel_stage'] = 0
        
        # 7. ENGAGEMENT DECAY PATTERN
        week1_end = first_date + pd.Timedelta(days=7)
        week2_end = first_date + pd.Timedelta(days=15)
        
        week1_events = user_events_copy[user_events_copy['event_date'] < week1_end]
        week2_events = user_events_copy[
            (user_events_copy['event_date'] >= week1_end) & 
            (user_events_copy['event_date'] <= week2_end)
        ]
        
        if len(week1_events) == 0:
            feature_dict['decay_pattern'] = 'No_Early_Activity'
        elif len(week2_events) == 0:
            feature_dict['decay_pattern'] = 'Complete_Dropout'
        else:
            decay_ratio = len(week2_events) / len(week1_events)
            if decay_ratio < 0.2:
                feature_dict['decay_pattern'] = 'Sharp_Decline'
            elif decay_ratio >= 0.5:
                feature_dict['decay_pattern'] = 'Stable_Engagement'
            else:
                feature_dict['decay_pattern'] = 'Moderate_Decline'
        
        features.append(feature_dict)
    
    return pd.DataFrame(features)

def save_to_database(features_df, engine):
    """
    Feature'ları database'e kaydet
    """
    
    print("💾 Saving features to database...")
    
    # Drop table if exists and create new one
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_non_paying_user_features"))
        conn.commit()
    
    # Save to database
    features_df.to_sql(
        'test_non_paying_user_features', 
        engine, 
        if_exists='replace',
        index=False,
        chunksize=5000
    )
    
    # Create indexes
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX idx_non_paying_user_id ON test_non_paying_user_features(user_id)"))
        conn.execute(text("CREATE INDEX idx_non_paying_target ON test_non_paying_user_features(first_year_revenue)"))
        conn.commit()
    
    print(f"   ✅ Saved {len(features_df):,} records to 'test_non_paying_user_features' table")

def analyze_features(features_df):
    """
    Feature'ları analiz et
    """
    
    print("\n📊 FEATURE ANALYSIS:")
    print("-" * 50)
    
    # Paying vs non-paying split
    paying_users = features_df[features_df['first_year_revenue'] > 0]
    non_paying_users = features_df[features_df['first_year_revenue'] == 0]
    
    print(f"Paying users: {len(paying_users):,} ({len(paying_users)/len(features_df)*100:.1f}%)")
    print(f"Non-paying users: {len(non_paying_users):,} ({len(non_paying_users)/len(features_df)*100:.1f}%)")
    
    # Feature discrimination analysis
    print(f"\n🎯 TOP DISCRIMINATIVE FEATURES:")
    print("-" * 50)
    
    numerical_features = [
        'total_events_15d', 'active_days_15d', 'paywall_event_ratio', 'early_activity_ratio'
    ]
    
    for feature in numerical_features:
        paying_mean = paying_users[feature].mean()
        non_paying_mean = non_paying_users[feature].mean()
        diff = abs(paying_mean - non_paying_mean)
        print(f"{feature:<25}: Paying={paying_mean:>6.2f} | Non-Paying={non_paying_mean:>6.2f} | Diff={diff:>6.2f}")
    
    # Categorical feature analysis
    print(f"\n📊 CATEGORICAL FEATURE DISTRIBUTIONS:")
    print("-" * 50)
    
    categorical_features = ['engagement_depth', 'funnel_stage', 'decay_pattern']
    
    for feature in categorical_features:
        print(f"\n{feature}:")
        value_counts = features_df[feature].value_counts()
        for value, count in value_counts.items():
            pct = count / len(features_df) * 100
            print(f"  {value:<20}: {count:>6,} ({pct:>5.1f}%)")

if __name__ == "__main__":
    features = create_non_paying_features_fast()
