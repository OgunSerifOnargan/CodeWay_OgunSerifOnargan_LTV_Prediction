import polars as pl
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

def create_pre_subscription_features_table():
    """Pre-subscription features tablosunu oluştur"""
    print("🗄️ Pre-subscription features tablosu oluşturuluyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Tabloyu sil ve yeniden oluştur
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS pre_subscription_features"))
        conn.commit()
        
        # Tablo oluştur
        create_table_sql = """
        CREATE TABLE test_pre_subscription_features (
            user_id VARCHAR(50) PRIMARY KEY,
            retention_risk_category VARCHAR(50),
            retention_confidence_score INTEGER,
            engagement_level VARCHAR(50),
            value_signal_category VARCHAR(50),
            pre_sub_pattern_length INTEGER,
            pre_sub_events_count INTEGER,
            pattern_complexity_score INTEGER,
            
            -- Binary Pattern Features (Top 5)
            is_paywall_free_trial BOOLEAN,
            is_paywall_paywall_free_trial BOOLEAN,
            is_paywall_only BOOLEAN,
            is_paywall_paywall_paywall BOOLEAN,
            is_paywall_free_trial_paywall BOOLEAN,
            
            -- Event Type Binary Features
            has_paywall BOOLEAN,
            has_free_trial BOOLEAN,
            has_auto_renew_off BOOLEAN,
            is_direct_sub BOOLEAN,
            
            -- Pattern String
            pattern_string TEXT
        )
        """
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✅ Tablo oluşturuldu")

def calculate_pre_subscription_features():
    """Pre-subscription features'ları hesapla"""
    print("🔄 Pre-subscription features hesaplanıyor...")
    
    # Parquet dosyasını oku
    print("📂 Veri yükleniyor...")
    df = pl.read_parquet('ltvprediction_case.parquet')
    df_pandas = df.to_pandas()
    
    # Event time'ları datetime'a çevir
    print("⏰ Event time'ları dönüştürülüyor...")
    df_pandas['event_datetime'] = pd.to_datetime(
        df_pandas['event_time'], unit='ms'
    )
    
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
    print("🔗 İlk subscription'lar ana dataframe'e ekleniyor...")
    df_pandas = df_pandas.merge(
        first_subscriptions[['user_id', 'event_datetime']], 
        on='user_id', 
        suffixes=('', '_first_sub')
    )
    
    # Subscription öncesi event'leri filtrele
    print("🔍 Subscription öncesi event'ler filtreleniyor...")
    pre_sub_events = df_pandas[
        df_pandas['event_datetime'] < df_pandas['event_datetime_first_sub']
    ].copy()
    
    print(f"📊 Subscription öncesi event'ler: {len(pre_sub_events):,}")
    
    # Her user için son 3 event'i al
    print("📋 Son 3 event'ler çıkarılıyor...")
    pre_sub_events = pre_sub_events.sort_values(['user_id', 'event_datetime'], ascending=[True, False])
    last_3_events = pre_sub_events.groupby('user_id').head(3).copy()
    
    # Pattern'leri oluştur
    print("🔧 Pattern'ler oluşturuluyor...")
    last_3_events = last_3_events.sort_values(['user_id', 'event_datetime'], ascending=[True, True])
    
    patterns = last_3_events.groupby('user_id').agg({
        'event_name': lambda x: ', '.join(x.tolist()),
        'event_datetime': 'count'
    }).reset_index()
    
    patterns.columns = ['user_id', 'pattern_string', 'pattern_length']
    
    # Direct subscription'ları ekle
    print("🎯 Direct subscription'lar ekleniyor...")
    all_subscribers = set(first_subscriptions['user_id'])
    pattern_subscribers = set(patterns['user_id'])
    direct_subscribers = all_subscribers - pattern_subscribers
    
    direct_sub_patterns = pd.DataFrame({
        'user_id': list(direct_subscribers),
        'pattern_string': 'direct_sub',
        'pattern_length': 0
    })
    
    # Tüm pattern'leri birleştir
    all_patterns = pd.concat([patterns, direct_sub_patterns], ignore_index=True)
    
    # Subscription öncesi event sayısını ekle
    print("📊 Event sayıları ekleniyor...")
    event_counts = pre_sub_events.groupby('user_id').size().reset_index(name='events_before_sub')
    all_patterns = all_patterns.merge(event_counts, on='user_id', how='left')
    all_patterns['events_before_sub'] = all_patterns['events_before_sub'].fillna(0).astype(int)
    
    print(f"📊 Toplam pattern: {len(all_patterns):,}")
    
    return all_patterns

def calculate_features_from_patterns(patterns_df):
    """Pattern'lerden feature'ları hesapla"""
    print("🧮 Feature'lar hesaplanıyor...")
    
    features = patterns_df.copy()
    
    # Binary Pattern Features (Top 5)
    print("🔢 Binary pattern features...")
    features['is_paywall_free_trial'] = features['pattern_string'] == 'paywall, free_trial'
    features['is_paywall_paywall_free_trial'] = features['pattern_string'] == 'paywall, paywall, free_trial'
    features['is_paywall_only'] = features['pattern_string'] == 'paywall'
    features['is_paywall_paywall_paywall'] = features['pattern_string'] == 'paywall, paywall, paywall'
    features['is_paywall_free_trial_paywall'] = features['pattern_string'] == 'paywall, free_trial, paywall'
    
    # Event Type Binary Features
    print("🔢 Event type binary features...")
    features['has_paywall'] = features['pattern_string'].str.contains('paywall', case=False)
    features['has_free_trial'] = features['pattern_string'].str.contains('free_trial', case=False)
    features['has_auto_renew_off'] = features['pattern_string'].str.contains('auto_renew_off', case=False)
    features['is_direct_sub'] = features['pattern_string'] == 'direct_sub'
    
    # Retention Risk Categories
    print("🎯 Retention risk categories...")
    def get_retention_risk_category(row):
        if row['pattern_string'] == 'direct_sub':
            return 'high_churn_risk'
        elif row['pattern_string'] == 'paywall':
            return 'moderate_churn_risk'
        elif 'free_trial' in row['pattern_string']:
            return 'low_churn_risk'
        else:
            return 'very_low_churn_risk'
    
    features['retention_risk_category'] = features.apply(get_retention_risk_category, axis=1)
    
    # Retention Confidence Score
    print("🎯 Retention confidence scores...")
    def get_retention_confidence_score(row):
        if row['pattern_string'] == 'direct_sub':
            return 5
        elif row['pattern_string'] == 'paywall':
            return 25
        elif 'free_trial' in row['pattern_string']:
            return 75
        else:
            return 95
    
    features['retention_confidence_score'] = features.apply(get_retention_confidence_score, axis=1)
    
    # Engagement Level
    print("📊 Engagement levels...")
    def get_engagement_level(row):
        if row['pattern_length'] == 0:
            return 'zero_engagement'
        elif row['pattern_length'] == 1:
            return 'low_engagement'
        elif row['pattern_length'] == 2:
            return 'medium_engagement'
        else:
            return 'high_engagement'
    
    features['engagement_level'] = features.apply(get_engagement_level, axis=1)
    
    # Value Signal Category
    print("💰 Value signal categories...")
    def get_value_signal_category(row):
        if row['pattern_string'] in ['direct_sub', 'paywall']:
            return 'low_value_signal'
        else:
            return 'high_value_signal'
    
    features['value_signal_category'] = features.apply(get_value_signal_category, axis=1)
    
    # Pattern Complexity Score
    print("🧩 Pattern complexity scores...")
    def get_pattern_complexity_score(row):
        if row['pattern_string'] == 'direct_sub':
            return 0
        elif row['pattern_string'] == 'paywall':
            return 20
        elif row['pattern_length'] == 2:
            return 60
        else:
            return 90
    
    features['pattern_complexity_score'] = features.apply(get_pattern_complexity_score, axis=1)
    
    # Rename columns for SQL
    features = features.rename(columns={
        'pattern_length': 'pre_sub_pattern_length',
        'events_before_sub': 'pre_sub_events_count'
    })
    
    print(f"✅ {len(features)} user için feature'lar hesaplandı")
    
    return features

def save_features_to_database(features_df):
    """Feature'ları database'e kaydet"""
    print("💾 Feature'lar database'e kaydediliyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Sadece gerekli kolonları seç
    columns_to_save = [
        'user_id', 'retention_risk_category', 'retention_confidence_score',
        'engagement_level', 'value_signal_category', 'pre_sub_pattern_length',
        'pre_sub_events_count', 'pattern_complexity_score',
        'is_paywall_free_trial', 'is_paywall_paywall_free_trial', 'is_paywall_only',
        'is_paywall_paywall_paywall', 'is_paywall_free_trial_paywall',
        'has_paywall', 'has_free_trial', 'has_auto_renew_off', 'is_direct_sub',
        'pattern_string'
    ]
    
    features_to_save = features_df[columns_to_save].copy()
    
    # Boolean kolonları düzelt
    boolean_columns = [
        'is_paywall_free_trial', 'is_paywall_paywall_free_trial', 'is_paywall_only',
        'is_paywall_paywall_paywall', 'is_paywall_free_trial_paywall',
        'has_paywall', 'has_free_trial', 'has_auto_renew_off', 'is_direct_sub'
    ]
    
    for col in boolean_columns:
        features_to_save[col] = features_to_save[col].astype(bool)
    
    # Database'e kaydet
    print("📤 Database'e yazılıyor...")
    features_to_save.to_sql(
        'test_pre_subscription_features', 
        engine, 
        if_exists='replace', 
        index=False,
        method='multi',
        chunksize=1000
    )
    
    print("✅ Feature'lar database'e kaydedildi")
    
    return features_to_save

def verify_features():
    """Feature'ları doğrula"""
    print("🔍 Feature'lar doğrulanıyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Tablo istatistikleri
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM pre_subscription_features"))
        total_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT retention_risk_category, COUNT(*) 
            FROM pre_subscription_features 
            GROUP BY retention_risk_category 
            ORDER BY COUNT(*) DESC
        """))
        retention_dist = result.fetchall()
        
        result = conn.execute(text("""
            SELECT engagement_level, COUNT(*) 
            FROM pre_subscription_features 
            GROUP BY engagement_level 
            ORDER BY COUNT(*) DESC
        """))
        engagement_dist = result.fetchall()
        
        result = conn.execute(text("""
            SELECT is_paywall_free_trial, COUNT(*) 
            FROM pre_subscription_features 
            GROUP BY is_paywall_free_trial
        """))
        paywall_trial_dist = result.fetchall()
    
    print(f"📊 Toplam kayıt: {total_count:,}")
    print(f"📊 Retention risk dağılımı:")
    for category, count in retention_dist:
        percentage = (count / total_count) * 100
        print(f"   {category}: {count:,} ({percentage:.1f}%)")
    
    print(f"📊 Engagement level dağılımı:")
    for level, count in engagement_dist:
        percentage = (count / total_count) * 100
        print(f"   {level}: {count:,} ({percentage:.1f}%)")
    
    print(f"📊 Paywall+Free Trial dağılımı:")
    for has_pattern, count in paywall_trial_dist:
        percentage = (count / total_count) * 100
        print(f"   {has_pattern}: {count:,} ({percentage:.1f}%)")

def main():
    """Ana fonksiyon"""
    print("🚀 PRE-SUBSCRIPTION FEATURES CREATION (ULTRA FAST)")
    print("=" * 80)
    
    # Tablo oluştur
    create_pre_subscription_features_table()
    
    # Pattern'leri hesapla
    patterns_df = calculate_pre_subscription_features()
    
    # Feature'ları hesapla
    features_df = calculate_features_from_patterns(patterns_df)
    
    # Database'e kaydet
    saved_features = save_features_to_database(features_df)
    
    # Doğrula
    verify_features()
    
    # Sonuçları kaydet
    saved_features.to_csv('pre_subscription_features_ultra_fast.csv', index=False)
    print(f"\n💾 Sonuçlar 'pre_subscription_features_ultra_fast.csv' dosyasına kaydedildi")
    
    print(f"\n🎉 PRE-SUBSCRIPTION FEATURES CREATION TAMAMLANDI!")

if __name__ == "__main__":
    main()
