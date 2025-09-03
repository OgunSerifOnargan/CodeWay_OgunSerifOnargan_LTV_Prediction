import polars as pl
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

def create_post_subscription_features_table():
    """Post-subscription features tablosunu oluştur"""
    print("🗄️ Post-subscription features tablosu oluşturuluyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Tabloyu sil ve yeniden oluştur
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS post_subscription_features"))
        conn.commit()
        
        # Tablo oluştur
        create_table_sql = """
        CREATE TABLE test_post_subscription_features (
            user_id VARCHAR(50) PRIMARY KEY,
            
            -- Tier 1: Critical Binary Features
            has_renewal_post_sub BOOLEAN,
            has_auto_renew_off_post_sub BOOLEAN,
            has_refund_post_sub BOOLEAN,
            is_multiple_subscriber BOOLEAN,
            has_paywall_post_sub BOOLEAN,
            
            -- Tier 2: Count & Numeric Features
            post_sub_events_count INTEGER,
            renewal_count_post_sub INTEGER,
            subscription_count_total INTEGER,
            post_sub_total_revenue DECIMAL(10,2),
            renewal_revenue_impact DECIMAL(10,2),
            
            -- Tier 3: Categorical Features
            post_sub_engagement_level VARCHAR(50),
            post_sub_pattern_category VARCHAR(50),
            churn_risk_post_sub VARCHAR(50),
            retention_potential_post_sub VARCHAR(50),
            
            -- Tier 4: Timing & Behavioral Features
            days_to_first_renewal_post_sub INTEGER,
            subscription_interval_avg DECIMAL(10,2),
            quick_renewal_flag BOOLEAN,
            post_sub_event_diversity INTEGER,
            post_sub_pattern_length INTEGER,
            
            -- Tier 5: Composite Scores
            post_sub_retention_score INTEGER,
            post_sub_revenue_efficiency DECIMAL(10,4),
            post_sub_risk_score INTEGER,
            
            -- Pattern String
            post_sub_pattern_string TEXT
        )
        """
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✅ Tablo oluşturuldu")

def calculate_post_subscription_features():
    """Post-subscription feature'larını hesapla"""
    print("📂 Veri yükleniyor...")
    df = pl.read_parquet('ltvprediction_case.parquet')
    df_pandas = df.to_pandas()
    
    print("⏰ Event time'ları dönüştürülüyor...")
    df_pandas['event_datetime'] = pd.to_datetime(df_pandas['event_time'], unit='ms')
    
    print(f"📊 Toplam events: {len(df_pandas):,}")
    
    # Her user için ilk subscription'ı bul
    print("🎯 İlk subscription'lar bulunuyor...")
    first_subscriptions = df_pandas[
        df_pandas['event_name'] == 'subscribe'
    ].groupby('user_id').agg({
        'event_datetime': 'min',
        'event_time': 'min'
    }).reset_index()
    
    print(f"📊 Toplam unique subscribers: {len(first_subscriptions):,}")
    
    # İlk subscription'ları ana dataframe'e ekle
    df_pandas = df_pandas.merge(
        first_subscriptions[['user_id', 'event_datetime']], 
        on='user_id', 
        suffixes=('', '_first_sub')
    )
    
    # Post-subscription event'leri filtrele
    post_sub_events = df_pandas[
        df_pandas['event_datetime'] > df_pandas['event_datetime_first_sub']
    ].copy()
    
    print(f"📊 Post-subscription event'ler: {len(post_sub_events):,}")
    
    # Her user için post-subscription pattern'lerini çıkar
    print("📋 Post-subscription pattern'ler çıkarılıyor...")
    patterns = post_sub_events.groupby('user_id').agg({
        'event_name': lambda x: ', '.join(x.tolist()),
        'event_datetime': 'count',
        'revenue': 'sum'
    }).reset_index()
    
    patterns.columns = ['user_id', 'post_sub_pattern_string', 'post_sub_events_count', 'post_sub_total_revenue']
    
    # Multiple subscription analizi
    print("🔄 Multiple subscription analizi...")
    subscription_counts = df_pandas[
        df_pandas['event_name'] == 'subscribe'
    ].groupby('user_id').size().reset_index(name='subscription_count_total')
    
    # Renewal timing analizi
    print("⏰ Renewal timing analizi...")
    renewal_timing = []
    
    for user_id in patterns['user_id']:
        user_post_events = post_sub_events[post_sub_events['user_id'] == user_id].copy()
        user_first_sub = first_subscriptions[first_subscriptions['user_id'] == user_id]['event_datetime'].iloc[0]
        
        # İlk renewal'ı bul
        user_renewals = user_post_events[user_post_events['event_name'] == 'renewal'].copy()
        
        if len(user_renewals) > 0:
            first_renewal = user_renewals.sort_values('event_datetime').iloc[0]
            days_to_first_renewal = (first_renewal['event_datetime'] - user_first_sub).days
        else:
            days_to_first_renewal = -1  # No renewal
        
        renewal_timing.append({
            'user_id': user_id,
            'days_to_first_renewal_post_sub': days_to_first_renewal
        })
    
    renewal_timing_df = pd.DataFrame(renewal_timing)
    
    # Multiple subscription timing analizi
    print("⏰ Multiple subscription timing analizi...")
    multiple_sub_timing = []
    
    for user_id in subscription_counts[subscription_counts['subscription_count_total'] > 1]['user_id']:
        user_subs = df_pandas[
            (df_pandas['user_id'] == user_id) & 
            (df_pandas['event_name'] == 'subscribe')
        ].sort_values('event_datetime')
        
        if len(user_subs) >= 2:
            intervals = []
            for i in range(1, len(user_subs)):
                interval = (user_subs.iloc[i]['event_datetime'] - user_subs.iloc[i-1]['event_datetime']).days
                intervals.append(interval)
            
            avg_interval = np.mean(intervals)
        else:
            avg_interval = 0
        
        multiple_sub_timing.append({
            'user_id': user_id,
            'subscription_interval_avg': avg_interval
        })
    
    multiple_sub_timing_df = pd.DataFrame(multiple_sub_timing)
    
    # Tüm feature'ları birleştir
    print("🔗 Feature'lar birleştiriliyor...")
    features = patterns.copy()
    
    # Subscription count ekle
    features = features.merge(subscription_counts, on='user_id', how='left')
    features['subscription_count_total'] = features['subscription_count_total'].fillna(1).astype(int)
    
    # Renewal timing ekle
    features = features.merge(renewal_timing_df, on='user_id', how='left')
    features['days_to_first_renewal_post_sub'] = features['days_to_first_renewal_post_sub'].fillna(-1).astype(int)
    
    # Multiple subscription timing ekle
    features = features.merge(multiple_sub_timing_df, on='user_id', how='left')
    features['subscription_interval_avg'] = features['subscription_interval_avg'].fillna(0)
    
    print(f"📊 Feature calculation tamamlandı: {len(features):,} user")
    
    return features

def calculate_features_from_patterns(features_df):
    """Pattern'lerden feature'ları hesapla"""
    print("🧮 Feature'lar hesaplanıyor...")
    
    features = features_df.copy()
    
    # Tier 1: Critical Binary Features
    features['has_renewal_post_sub'] = features['post_sub_pattern_string'].str.contains('renewal', case=False)
    features['has_auto_renew_off_post_sub'] = features['post_sub_pattern_string'].str.contains('auto_renew_off', case=False)
    features['has_refund_post_sub'] = features['post_sub_pattern_string'].str.contains('refund', case=False)
    features['is_multiple_subscriber'] = features['subscription_count_total'] > 1
    features['has_paywall_post_sub'] = features['post_sub_pattern_string'].str.contains('paywall', case=False)
    
    # Tier 2: Count Features
    features['renewal_count_post_sub'] = features['post_sub_pattern_string'].str.count('renewal')
    
    # Tier 3: Categorical Features
    # Engagement Level
    def get_engagement_level(row):
        if row['post_sub_events_count'] <= 5:
            return 'low_engagement'
        elif row['post_sub_events_count'] <= 20:
            return 'medium_engagement'
        else:
            return 'high_engagement'
    features['post_sub_engagement_level'] = features.apply(get_engagement_level, axis=1)
    
    # Pattern Category
    def get_pattern_category(row):
        pattern = row['post_sub_pattern_string']
        if 'renewal' in pattern and 'auto_renew_off' not in pattern and 'refund' not in pattern:
            return 'renewal_only'
        elif 'auto_renew_off' in pattern and 'renewal' not in pattern:
            return 'auto_renew_off_only'
        elif 'refund' in pattern:
            return 'refund_pattern'
        else:
            return 'mixed_pattern'
    features['post_sub_pattern_category'] = features.apply(get_pattern_category, axis=1)
    
    # Churn Risk
    def get_churn_risk(row):
        if row['has_refund_post_sub']:
            return 'high_risk'
        elif row['has_auto_renew_off_post_sub'] and not row['has_renewal_post_sub']:
            return 'high_risk'
        elif not row['has_renewal_post_sub']:
            return 'medium_risk'
        else:
            return 'low_risk'
    features['churn_risk_post_sub'] = features.apply(get_churn_risk, axis=1)
    
    # Retention Potential
    def get_retention_potential(row):
        if row['renewal_count_post_sub'] >= 2:
            return 'high_potential'
        elif row['has_renewal_post_sub']:
            return 'medium_potential'
        else:
            return 'low_potential'
    features['retention_potential_post_sub'] = features.apply(get_retention_potential, axis=1)
    
    # Tier 4: Timing Features
    features['quick_renewal_flag'] = (features['days_to_first_renewal_post_sub'] >= 0) & (features['days_to_first_renewal_post_sub'] <= 7.80)
    
    # Event Diversity
    def get_event_diversity(row):
        if pd.isna(row['post_sub_pattern_string']) or row['post_sub_pattern_string'] == '':
            return 0
        events = row['post_sub_pattern_string'].split(', ')
        return len(set(events))
    features['post_sub_event_diversity'] = features.apply(get_event_diversity, axis=1)
    
    # Pattern Length
    def get_pattern_length(row):
        if pd.isna(row['post_sub_pattern_string']) or row['post_sub_pattern_string'] == '':
            return 0
        return len(row['post_sub_pattern_string'].split(', '))
    features['post_sub_pattern_length'] = features.apply(get_pattern_length, axis=1)
    
    # Tier 5: Composite Scores
    # Retention Score (0-100)
    def get_retention_score(row):
        score = 0
        if row['has_renewal_post_sub']: score += 40
        if not row['has_auto_renew_off_post_sub']: score += 30
        if not row['has_refund_post_sub']: score += 20
        if row['renewal_count_post_sub'] >= 2: score += 10
        return score
    features['post_sub_retention_score'] = features.apply(get_retention_score, axis=1)
    
    # Revenue Efficiency
    features['post_sub_revenue_efficiency'] = np.where(
        features['post_sub_events_count'] > 0,
        features['post_sub_total_revenue'] / features['post_sub_events_count'],
        0
    )
    
    # Risk Score (0-100)
    def get_risk_score(row):
        score = 0
        if row['has_refund_post_sub']: score += 50
        if row['has_auto_renew_off_post_sub']: score += 30
        if not row['has_renewal_post_sub']: score += 20
        return score
    features['post_sub_risk_score'] = features.apply(get_risk_score, axis=1)
    
    # Revenue Impact
    features['renewal_revenue_impact'] = np.where(
        features['has_renewal_post_sub'],
        5.17,  # Renewal yapanların ortalama farkı
        0
    )
    
    return features

def save_features_to_database(features_df):
    """Feature'ları database'e kaydet"""
    print("💾 Feature'lar database'e kaydediliyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Sadece gerekli kolonları seç
    columns_to_save = [
        'user_id', 'has_renewal_post_sub', 'has_auto_renew_off_post_sub', 
        'has_refund_post_sub', 'is_multiple_subscriber', 'has_paywall_post_sub',
        'post_sub_events_count', 'renewal_count_post_sub', 'subscription_count_total',
        'post_sub_total_revenue', 'renewal_revenue_impact', 'post_sub_engagement_level',
        'post_sub_pattern_category', 'churn_risk_post_sub', 'retention_potential_post_sub',
        'days_to_first_renewal_post_sub', 'subscription_interval_avg', 'quick_renewal_flag',
        'post_sub_event_diversity', 'post_sub_pattern_length', 'post_sub_retention_score',
        'post_sub_revenue_efficiency', 'post_sub_risk_score', 'post_sub_pattern_string'
    ]
    
    features_to_save = features_df[columns_to_save].copy()
    
    # Boolean kolonları düzelt
    boolean_columns = ['has_renewal_post_sub', 'has_auto_renew_off_post_sub', 
                      'has_refund_post_sub', 'is_multiple_subscriber', 
                      'has_paywall_post_sub', 'quick_renewal_flag']
    
    for col in boolean_columns:
        features_to_save[col] = features_to_save[col].astype(bool)
    
    # Database'e kaydet
    features_to_save.to_sql('test_post_subscription_features', engine, if_exists='replace', index=False, method='multi', chunksize=1000)
    
    print(f"✅ {len(features_to_save):,} feature database'e kaydedildi")
    
    return features_to_save

def verify_features():
    """Feature'ları doğrula"""
    print("🔍 Feature'lar doğrulanıyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    with engine.connect() as conn:
        # Toplam kayıt sayısını kontrol et
        result = conn.execute(text("SELECT COUNT(*) FROM post_subscription_features"))
        count = result.fetchone()[0]
        print(f"📊 Toplam kayıt: {count:,}")
        
        # Örnek kayıtları göster
        result = conn.execute(text("SELECT * FROM post_subscription_features LIMIT 5"))
        sample_data = result.fetchall()
        
        print("\n📋 Örnek Kayıtlar:")
        for row in sample_data:
            print(f"   User ID: {row[0]}")
            print(f"   Has Renewal: {row[1]}")
            print(f"   Events Count: {row[6]}")
            print(f"   Revenue: ${row[9]:.2f}")
            print(f"   Engagement Level: {row[11]}")
            print(f"   Retention Score: {row[20]}")
            print("   ---")
    
    print("✅ Feature verification tamamlandı")

def main():
    """Ana fonksiyon"""
    print("🔄 POST-SUBSCRIPTION FEATURES CREATION")
    print("=" * 80)
    
    # Tablo oluştur
    create_post_subscription_features_table()
    
    # Feature'ları hesapla
    features_df = calculate_post_subscription_features()
    
    # Pattern'lerden feature'ları çıkar
    features_df = calculate_features_from_patterns(features_df)
    
    # Database'e kaydet
    saved_features = save_features_to_database(features_df)
    
    # Doğrula
    verify_features()
    
    # CSV olarak da kaydet
    saved_features.to_csv('post_subscription_features_ultra_fast.csv', index=False)
    
    print(f"\n💾 Sonuçlar kaydedildi:")
    print(f"   - 'post_subscription_features' (PostgreSQL table)")
    print(f"   - 'post_subscription_features_ultra_fast.csv'")
    
    print(f"\n🎉 POST-SUBSCRIPTION FEATURES CREATION TAMAMLANDI!")
    print(f"📊 Toplam {len(saved_features):,} user için {len(saved_features.columns)-1} feature oluşturuldu")

if __name__ == "__main__":
    main()
