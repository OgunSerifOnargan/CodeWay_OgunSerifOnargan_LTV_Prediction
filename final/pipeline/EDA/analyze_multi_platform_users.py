import polars as pl
from tqdm import tqdm

def analyze_multi_platform_users():
    """Farklı OS ve country'lerden giriş yapan kullanıcıların baskınlık analizini yapan script"""
    print("🔍 Multi-Platform User Baskınlık Analizi...")
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    print(f"📊 Toplam satır: {len(df):,}")
    print(f"📊 Unique user sayısı: {df['user_id'].n_unique():,}")
    
    # Multi-OS users
    print(f"\n🖥️  MULTI-OS USER ANALİZİ:")
    user_os_counts = df.group_by('user_id').agg([
        pl.col('operating_system').n_unique().alias('unique_os_count'),
        pl.col('operating_system').alias('all_os'),
        pl.col('operating_system').count().alias('total_events')
    ])
    
    multi_os_users = user_os_counts.filter(pl.col('unique_os_count') > 1)
    
    if len(multi_os_users) > 0:
        print(f"   Multi-OS user sayısı: {len(multi_os_users):,}")
        
        # Her multi-OS user için OS distribution analizi
        print(f"\n📊 Multi-OS User'ların OS Dağılımı:")
        
        for i, row in enumerate(multi_os_users.iter_rows()):
            user_id, unique_count, all_os, total_events = row
            
            # OS bazında event sayılarını hesapla
            os_counts = {}
            for os in all_os:
                os_counts[os] = os_counts.get(os, 0) + 1
            
            # Baskın OS'u bul
            dominant_os = max(os_counts.items(), key=lambda x: x[1])
            dominant_percentage = (dominant_os[1] / total_events) * 100
            
            print(f"   {i+1}. {user_id}:")
            print(f"      Total events: {total_events}")
            for os, count in os_counts.items():
                percentage = (count / total_events) * 100
                print(f"      {os}: {count} events ({percentage:.1f}%)")
            print(f"      Baskın OS: {dominant_os[0]} ({dominant_percentage:.1f}%)")
            print()
            
            if i >= 9:  # İlk 10 user'ı göster
                break
    else:
        print(f"   Multi-OS user yok!")
    
    # Multi-country users
    print(f"\n🌍 MULTI-COUNTRY USER ANALİZİ:")
    user_country_counts = df.group_by('user_id').agg([
        pl.col('country').n_unique().alias('unique_country_count'),
        pl.col('country').alias('all_countries'),
        pl.col('country').count().alias('total_events')
    ])
    
    multi_country_users = user_country_counts.filter(pl.col('unique_country_count') > 1)
    
    if len(multi_country_users) > 0:
        print(f"   Multi-country user sayısı: {len(multi_country_users):,}")
        
        # Her multi-country user için country distribution analizi
        print(f"\n📊 Multi-Country User'ların Country Dağılımı:")
        
        for i, row in enumerate(multi_country_users.iter_rows()):
            user_id, unique_count, all_countries, total_events = row
            
            # Country bazında event sayılarını hesapla
            country_counts = {}
            for country in all_countries:
                country_counts[country] = country_counts.get(country, 0) + 1
            
            # Baskın country'yi bul
            dominant_country = max(country_counts.items(), key=lambda x: x[1])
            dominant_percentage = (dominant_country[1] / total_events) * 100
            
            print(f"   {i+1}. {user_id}:")
            print(f"      Total events: {total_events}")
            for country, count in country_counts.items():
                percentage = (count / total_events) * 100
                print(f"      {country}: {count} events ({percentage:.1f}%)")
            print(f"      Baskın Country: {dominant_country[0]} ({dominant_percentage:.1f}%)")
            print()
            
            if i >= 9:  # İlk 10 user'ı göster
                break
    else:
        print(f"   Multi-country user yok!")
    
    # Baskınlık istatistikleri
    print(f"\n📈 BASKINLIK İSTATİSTİKLERİ:")
    
    # Multi-OS users için baskınlık analizi
    if len(multi_os_users) > 0:
        print(f"\n🖥️  Multi-OS Users Baskınlık Analizi:")
        dominant_percentages = []
        
        for row in multi_os_users.iter_rows():
            user_id, unique_count, all_os, total_events = row
            
            os_counts = {}
            for os in all_os:
                os_counts[os] = os_counts.get(os, 0) + 1
            
            dominant_os = max(os_counts.items(), key=lambda x: x[1])
            dominant_percentage = (dominant_os[1] / total_events) * 100
            dominant_percentages.append(dominant_percentage)
        
        print(f"   Ortalama baskınlık: {sum(dominant_percentages)/len(dominant_percentages):.1f}%")
        print(f"   En yüksek baskınlık: {max(dominant_percentages):.1f}%")
        print(f"   En düşük baskınlık: {min(dominant_percentages):.1f}%")
        
        # Baskınlık kategorileri
        high_dominance = sum(1 for p in dominant_percentages if p >= 80)
        medium_dominance = sum(1 for p in dominant_percentages if 60 <= p < 80)
        low_dominance = sum(1 for p in dominant_percentages if p < 60)
        
        print(f"   Yüksek baskınlık (≥80%): {high_dominance} user")
        print(f"   Orta baskınlık (60-80%): {medium_dominance} user")
        print(f"   Düşük baskınlık (<60%): {low_dominance} user")
    
    # Multi-country users için baskınlık analizi
    if len(multi_country_users) > 0:
        print(f"\n🌍 Multi-Country Users Baskınlık Analizi:")
        dominant_percentages = []
        
        for row in multi_country_users.iter_rows():
            user_id, unique_count, all_countries, total_events = row
            
            country_counts = {}
            for country in all_countries:
                country_counts[country] = country_counts.get(country, 0) + 1
            
            dominant_country = max(country_counts.items(), key=lambda x: x[1])
            dominant_percentage = (dominant_country[1] / total_events) * 100
            dominant_percentages.append(dominant_percentage)
        
        print(f"   Ortalama baskınlık: {sum(dominant_percentages)/len(dominant_percentages):.1f}%")
        print(f"   En yüksek baskınlık: {max(dominant_percentages):.1f}%")
        print(f"   En düşük baskınlık: {min(dominant_percentages):.1f}%")
        
        # Baskınlık kategorileri
        high_dominance = sum(1 for p in dominant_percentages if p >= 80)
        medium_dominance = sum(1 for p in dominant_percentages if 60 <= p < 80)
        low_dominance = sum(1 for p in dominant_percentages if p < 60)
        
        print(f"   Yüksek baskınlık (≥80%): {high_dominance} user")
        print(f"   Orta baskınlık (60-80%): {medium_dominance} user")
        print(f"   Düşük baskınlık (<60%): {low_dominance} user")

if __name__ == "__main__":
    analyze_multi_platform_users()
