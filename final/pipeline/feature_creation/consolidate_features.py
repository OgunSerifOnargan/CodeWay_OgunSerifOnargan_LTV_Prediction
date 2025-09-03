import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

def create_consolidated_features_table():
    """Consolidated features tablosunu oluştur"""
    print("🗄️ Consolidated features tablosu oluşturuluyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Tabloyu sil ve yeniden oluştur
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS consolidated_features"))
        conn.commit()
        
        # Tablo oluştur (user_id PRIMARY KEY)
        create_table_sql = """
        CREATE TABLE test_consolidated_features (
            user_id VARCHAR(50) PRIMARY KEY
        )
        """
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✅ Consolidated features tablosu oluşturuldu")

def load_feature_tables():
    """Tüm feature tablolarını yükle"""
    print("📂 Feature tabloları yükleniyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Tüm feature tablolarını yükle
    feature_tables = {}
    
    # User-level tablolar
    user_level_tables = [
        'event_name_features', 
        'post_subscription_features',
        'pre_subscription_features',
        'revenue_features'
    ]
    
    # Country-level tablolar
    country_level_tables = [
        'country_features'
    ]
    
    # User-level tabloları yükle
    for table_name in tqdm(user_level_tables, desc="User-level tablolar yükleniyor"):
        try:
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, engine)
            feature_tables[table_name] = df
            print(f"   ✅ {table_name}: {len(df):,} kayıt, {len(df.columns)} kolon")
        except Exception as e:
            print(f"   ❌ {table_name}: Hata - {e}")
    
    # Country-level tabloları yükle
    for table_name in tqdm(country_level_tables, desc="Country-level tablolar yükleniyor"):
        try:
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, engine)
            feature_tables[table_name] = df
            print(f"   ✅ {table_name}: {len(df):,} kayıt, {len(df.columns)} kolon")
        except Exception as e:
            print(f"   ❌ {table_name}: Hata - {e}")
    
    return feature_tables

def load_user_country_mapping():
    """User-country mapping'ini yükle"""
    print("🌍 User-country mapping yükleniyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # raw_dataset'ten user-country mapping'ini al
    query = """
    SELECT DISTINCT user_id, country 
    FROM raw_dataset 
    WHERE country IS NOT NULL
    """
    
    user_country_df = pd.read_sql(query, engine)
    print(f"   ✅ User-country mapping: {len(user_country_df):,} kayıt")
    
    return user_country_df

def merge_feature_tables(feature_tables, user_country_df):
    """Feature tablolarını birleştir"""
    print("\n🔗 Feature tabloları birleştiriliyor...")
    
    # User-level tabloları birleştir
    user_level_tables = ['event_name_features', 'post_subscription_features', 'pre_subscription_features', 'revenue_features']
    
    # İlk user-level tabloyu base olarak al
    base_table = None
    for table_name in user_level_tables:
        if table_name in feature_tables:
            df = feature_tables[table_name]
            if base_table is None:
                base_table = df.copy()
                print(f"   Base table: {table_name} ({len(base_table):,} user)")
            else:
                # LEFT JOIN ile birleştir
                before_count = len(base_table)
                base_table = base_table.merge(df, on='user_id', how='left', suffixes=('', f'_{table_name}'))
                after_count = len(base_table)
                print(f"   JOIN {table_name}: {before_count:,} -> {after_count:,} user")
    
    # Country features'ı ekle
    if 'country_features' in feature_tables and len(user_country_df) > 0:
        print("\n🌍 Country features ekleniyor...")
        
        # User-country mapping'i base table'a ekle
        before_count = len(base_table)
        base_table = base_table.merge(user_country_df, on='user_id', how='left')
        after_count = len(base_table)
        print(f"   JOIN user_country_mapping: {before_count:,} -> {after_count:,} user")
        
        # Country features'ı ekle
        country_df = feature_tables['country_features']
        before_count = len(base_table)
        base_table = base_table.merge(country_df, on='country', how='left', suffixes=('', '_country'))
        after_count = len(base_table)
        print(f"   JOIN country_features: {before_count:,} -> {after_count:,} user")
    
    print(f"\n📊 Birleştirme tamamlandı: {len(base_table):,} user, {len(base_table.columns)} kolon")
    
    return base_table

def analyze_duplicate_features(consolidated_df):
    """Duplicate feature'ları analiz et"""
    print("\n🔍 DUPLICATE FEATURE ANALİZİ...")
    
    # Kolon isimlerini analiz et
    columns = consolidated_df.columns.tolist()
    
    # user_id ve country hariç diğer kolonları analiz et
    feature_columns = [col for col in columns if col not in ['user_id', 'country']]
    
    print(f"📊 Toplam feature sayısı: {len(feature_columns)}")
    
    # Duplicate kolon isimleri
    duplicate_columns = []
    for col in feature_columns:
        if columns.count(col) > 1:
            duplicate_columns.append(col)
    
    if duplicate_columns:
        print(f"⚠️ Duplicate kolon isimleri bulundu: {len(duplicate_columns)}")
        for col in duplicate_columns:
            print(f"   - {col}")
    else:
        print("✅ Duplicate kolon ismi yok")
    
    # Benzer isimli kolonlar (farklı suffix'ler)
    similar_columns = {}
    for col in feature_columns:
        base_name = col.split('_')[0] if '_' in col else col
        if base_name not in similar_columns:
            similar_columns[base_name] = []
        similar_columns[base_name].append(col)
    
    # Birden fazla kolonu olan base name'ler
    multiple_columns = {k: v for k, v in similar_columns.items() if len(v) > 1}
    
    if multiple_columns:
        print(f"\n📊 Benzer isimli kolonlar:")
        for base_name, cols in multiple_columns.items():
            print(f"   {base_name}: {cols}")
    
    return duplicate_columns, multiple_columns

def analyze_multicollinearity(consolidated_df):
    """Multicollinearity analizi"""
    print("\n📊 MULTICOLLINEARITY ANALİZİ...")
    
    # Sadece numeric kolonları al
    numeric_columns = consolidated_df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_columns = [col for col in numeric_columns if col not in ['user_id']]
    
    print(f"📊 Numeric feature sayısı: {len(numeric_columns)}")
    
    if len(numeric_columns) > 1:
        # Correlation matrix hesapla
        correlation_matrix = consolidated_df[numeric_columns].corr()
        
        # Yüksek correlation'ları bul
        high_correlation_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.8:  # 0.8 threshold
                    col1 = correlation_matrix.columns[i]
                    col2 = correlation_matrix.columns[j]
                    high_correlation_pairs.append((col1, col2, corr_value))
        
        if high_correlation_pairs:
            print(f"⚠️ Yüksek correlation (>0.8) bulunan feature çiftleri: {len(high_correlation_pairs)}")
            for col1, col2, corr in high_correlation_pairs[:10]:  # İlk 10'u göster
                print(f"   {col1} <-> {col2}: {corr:.3f}")
        else:
            print("✅ Yüksek correlation bulunamadı")
    
    return numeric_columns

def save_consolidated_features(consolidated_df):
    """Consolidated features'ı database'e kaydet"""
    print("\n💾 Consolidated features database'e kaydediliyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # user_id'yi ilk kolon yap
    columns = ['user_id'] + [col for col in consolidated_df.columns if col != 'user_id']
    consolidated_df = consolidated_df[columns]
    
    # Database'e kaydet
    consolidated_df.to_sql('test_consolidated_features', engine, if_exists='replace', index=False, method='multi', chunksize=1000)
    
    print(f"✅ {len(consolidated_df):,} user, {len(consolidated_df.columns)} kolon kaydedildi")
    
    return consolidated_df

def verify_consolidated_features():
    """Consolidated features'ı doğrula"""
    print("\n🔍 Consolidated features doğrulanıyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    with engine.connect() as conn:
        # Toplam kayıt sayısını kontrol et
        result = conn.execute(text("SELECT COUNT(*) FROM consolidated_features"))
        count = result.fetchone()[0]
        print(f"📊 Toplam kayıt: {count:,}")
        
        # Kolon sayısını kontrol et
        result = conn.execute(text("SELECT * FROM consolidated_features LIMIT 1"))
        columns = result.keys()
        print(f"📊 Toplam kolon: {len(columns)}")
        
        # Örnek kayıtları göster
        result = conn.execute(text("SELECT * FROM consolidated_features LIMIT 3"))
        sample_data = result.fetchall()
        
        print("\n📋 Örnek Kayıtlar:")
        for i, row in enumerate(sample_data, 1):
            print(f"   User {i}: {row[0]} - {len(row)} kolon")
    
    print("✅ Verification tamamlandı")

def create_feature_summary_report(consolidated_df, duplicate_columns, multiple_columns, numeric_columns):
    """Feature summary raporu oluştur"""
    print("\n📋 FEATURE SUMMARY RAPORU...")
    
    # Feature kategorileri
    feature_categories = {
        'country_features': [col for col in consolidated_df.columns if 'country' in col.lower() and col not in ['country']],
        'event_name_features': [col for col in consolidated_df.columns if 'event' in col.lower() and 'name' in col.lower()],
        'post_subscription_features': [col for col in consolidated_df.columns if 'post_sub' in col.lower()],
        'pre_subscription_features': [col for col in consolidated_df.columns if 'pre_sub' in col.lower()],
        'revenue_features': [col for col in consolidated_df.columns if 'revenue' in col.lower()],
        'other_features': [col for col in consolidated_df.columns if col not in ['user_id', 'country'] and 
                          not any(cat in col.lower() for cat in ['country', 'event', 'post_sub', 'pre_sub', 'revenue'])]
    }
    
    print("📊 Feature Kategorileri:")
    for category, features in feature_categories.items():
        print(f"   {category}: {len(features)} feature")
        if len(features) <= 5:  # 5'ten azsa göster
            for feature in features:
                print(f"     - {feature}")
    
    # Data types
    data_types = consolidated_df.dtypes.value_counts()
    print(f"\n📊 Data Types:")
    for dtype, count in data_types.items():
        print(f"   {dtype}: {count} kolon")
    
    # Missing values
    missing_values = consolidated_df.isnull().sum()
    missing_features = missing_values[missing_values > 0]
    
    if len(missing_features) > 0:
        print(f"\n⚠️ Missing values olan feature'lar: {len(missing_features)}")
        for feature, missing_count in missing_features.head(10).items():
            missing_percentage = (missing_count / len(consolidated_df)) * 100
            print(f"   {feature}: {missing_count:,} ({missing_percentage:.1f}%)")
    else:
        print("\n✅ Missing value yok")

def main():
    """Ana fonksiyon"""
    print("🔄 FEATURE CONSOLIDATION")
    print("=" * 80)
    
    # Consolidated features tablosunu oluştur
    create_consolidated_features_table()
    
    # Feature tablolarını yükle
    feature_tables = load_feature_tables()
    
    # User-country mapping'ini yükle
    user_country_df = load_user_country_mapping()
    
    # Feature tablolarını birleştir
    consolidated_df = merge_feature_tables(feature_tables, user_country_df)
    
    # Duplicate feature analizi
    duplicate_columns, multiple_columns = analyze_duplicate_features(consolidated_df)
    
    # Multicollinearity analizi
    numeric_columns = analyze_multicollinearity(consolidated_df)
    
    # Feature summary raporu
    create_feature_summary_report(consolidated_df, duplicate_columns, multiple_columns, numeric_columns)
    
    # Database'e kaydet
    saved_df = save_consolidated_features(consolidated_df)
    
    # Doğrula
    verify_consolidated_features()
    
    # CSV olarak da kaydet
    saved_df.to_csv('consolidated_features.csv', index=False)
    
    print(f"\n💾 Sonuçlar kaydedildi:")
    print(f"   - 'consolidated_features' (PostgreSQL table)")
    print(f"   - 'consolidated_features.csv'")
    
    print(f"\n🎉 FEATURE CONSOLIDATION TAMAMLANDI!")
    print(f"📊 Toplam {len(saved_df):,} user için {len(saved_df.columns)-1} feature birleştirildi")

if __name__ == "__main__":
    main()
