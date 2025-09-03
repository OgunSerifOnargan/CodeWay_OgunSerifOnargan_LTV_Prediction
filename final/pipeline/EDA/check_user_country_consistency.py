import polars as pl
from tqdm import tqdm

def check_user_country_consistency():
    """User'ların country tutarlılığını kontrol eder"""
    print("🌍 User Country Tutarlılığı Kontrol Ediliyor...")
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    print(f"📊 Toplam satır: {len(df):,}")
    print(f"📊 Unique user sayısı: {df['user_id'].n_unique():,}")
    
    # User bazında unique country sayısını hesapla
    user_country_counts = df.group_by('user_id').agg([
        pl.col('country').n_unique().alias('unique_country_count'),
        pl.col('country').alias('all_countries')
    ])
    
    print(f"\n🌍 User Country Analizi:")
    
    # Unique country count distribution
    country_count_dist = user_country_counts.group_by('unique_country_count').len().sort('unique_country_count')
    
    for row in country_count_dist.iter_rows():
        count, user_count = row
        percentage = (user_count / len(user_country_counts)) * 100
        print(f"   {count} unique country: {user_count:,} user ({percentage:.2f}%)")
    
    # Birden fazla country'si olan user'ları bul
    multiple_country_users = user_country_counts.filter(pl.col('unique_country_count') > 1)
    
    if len(multiple_country_users) > 0:
        print(f"\n⚠️  BİRDEN FAZLA COUNTRY'Sİ OLAN USER'LAR:")
        print(f"   Toplam: {len(multiple_country_users):,} user")
        
        # İlk 10 user'ın detayını göster
        print(f"\n📋 İlk 10 User'ın Country Detayları:")
        for i, row in enumerate(multiple_country_users.head(10).iter_rows()):
            user_id, unique_count, all_countries = row
            unique_country_list = list(set(all_countries))
            print(f"   {i+1}. {user_id}: {unique_country_list}")
        
        # En çok farklı country'si olan user'ları göster
        print(f"\n🏆 En Çok Farklı Country'si Olan User'lar:")
        top_users = multiple_country_users.sort('unique_country_count', descending=True).head(5)
        for i, row in enumerate(top_users.iter_rows()):
            user_id, unique_count, all_countries = row
            unique_country_list = list(set(all_countries))
            print(f"   {i+1}. {user_id}: {unique_count} countries - {unique_country_list}")
    else:
        print(f"\n✅ TÜM USER'LAR TUTARLI!")
        print(f"   Her user'ın sadece 1 country'si var")
    
    # Country distribution
    print(f"\n🌍 Country Dağılımı:")
    country_dist = df.group_by('country').len().sort('len', descending=True)
    
    print(f"   Top 10 Countries:")
    for i, row in enumerate(country_dist.head(10).iter_rows()):
        country, count = row
        percentage = (count / len(df)) * 100
        print(f"   {i+1}. {country}: {count:,} event ({percentage:.2f}%)")
    
    # User bazında country distribution
    print(f"\n🌍 User Bazında Country Dağılımı:")
    user_country_dist = df.group_by('country').agg([
        pl.col('user_id').n_unique().alias('unique_users')
    ]).sort('unique_users', descending=True)
    
    print(f"   Top 10 Countries:")
    for i, row in enumerate(user_country_dist.head(10).iter_rows()):
        country, unique_users = row
        percentage = (unique_users / df['user_id'].n_unique()) * 100
        print(f"   {i+1}. {country}: {unique_users:,} unique user ({percentage:.2f}%)")
    
    # Null country kontrolü
    null_country_df = df.filter(pl.col('country').is_null())
    null_country_count = len(null_country_df)
    if null_country_count > 0:
        print(f"\n⚠️  NULL COUNTRY KONTROLÜ:")
        print(f"   Null country event sayısı: {null_country_count:,}")
        print(f"   Null country user sayısı: {null_country_df['user_id'].n_unique():,}")
    else:
        print(f"\n✅ NULL COUNTRY YOK!")
        print(f"   Tüm event'lerde country bilgisi mevcut")

if __name__ == "__main__":
    check_user_country_consistency()
