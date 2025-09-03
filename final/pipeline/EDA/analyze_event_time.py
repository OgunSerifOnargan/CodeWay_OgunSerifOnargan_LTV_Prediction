import polars as pl
from datetime import datetime, timedelta

def analyze_event_time():
    """event_time sütununun birimini, formatını ve kullanım amacını analiz eder"""
    print("🔍 Event Time Analizi...")
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    print(f"📊 Toplam satır: {len(df):,}")
    
    # Event time sütununu incele
    print(f"\n📅 EVENT_TIME SÜTUNU ANALİZİ:")
    print("=" * 50)
    
    # İlk birkaç satırı göster
    print(f"\n🔍 İlk 5 satır event_time değerleri:")
    sample_times = df.select('event_time').head(5)
    for i, row in enumerate(sample_times.iter_rows()):
        print(f"   {i+1}. {row[0]}")
    
    # Event time istatistikleri
    print(f"\n📊 Event Time İstatistikleri:")
    
    # Min, max değerler
    min_time = df.select('event_time').min().item()
    max_time = df.select('event_time').max().item()
    
    print(f"   En erken event: {min_time}")
    print(f"   En geç event: {max_time}")
    
    # Time range hesapla
    if isinstance(min_time, (int, float)) and isinstance(max_time, (int, float)):
        time_range = max_time - min_time
        print(f"   Time range: {time_range:,}")
        
        # Birim tahmini
        print(f"\n🔍 BİRİM TAHMİNİ:")
        
        # Unix timestamp (milisaniye) olabilir mi?
        if min_time > 1000000000000:  # 2001'den sonra
            print(f"   Unix timestamp (milisaniye) olabilir:")
            min_date = datetime.fromtimestamp(min_time / 1000)
            max_date = datetime.fromtimestamp(max_time / 1000)
            print(f"   En erken: {min_date}")
            print(f"   En geç: {max_date}")
            print(f"   Toplam süre: {max_date - min_date}")
        
        # Unix timestamp olabilir mi? (1970'den itibaren saniye)
        elif min_time > 1000000000:  # 2001'den sonra
            print(f"   Unix timestamp (saniye) olabilir:")
            min_date = datetime.fromtimestamp(min_time)
            max_date = datetime.fromtimestamp(max_time)
            print(f"   En erken: {min_date}")
            print(f"   En geç: {max_date}")
            print(f"   Toplam süre: {max_date - min_date}")
        
        # Microsecond olabilir mi?
        elif min_time > 1000000000000000:  # 2001'den sonra
            print(f"   Unix timestamp (mikrosaniye) olabilir:")
            min_date = datetime.fromtimestamp(min_time / 1000000)
            max_date = datetime.fromtimestamp(max_time / 1000000)
            print(f"   En erken: {min_date}")
            print(f"   En geç: {max_date}")
            print(f"   Toplam süre: {max_date - min_date}")
        
        else:
            print(f"   Bilinmeyen format: {min_time} - {max_time}")
    
    # Event time dağılımı
    print(f"\n📈 EVENT TIME DAĞILIMI:")
    
    # Günlük dağılım (eğer timestamp ise)
    if isinstance(min_time, (int, float)) and min_time > 1000000000000:
        # Unix timestamp (milisaniye)'i datetime'a çevir
        df_with_date = df.with_columns([
            pl.col('event_time').cast(pl.Int64).map_elements(
                lambda x: datetime.fromtimestamp(x / 1000) if x else None
            ).alias('event_datetime')
        ])
        
        # Günlük event sayıları
        daily_events = df_with_date.group_by(
            pl.col('event_datetime').dt.date().alias('date')
        ).agg([
            pl.len().alias('event_count')
        ]).sort('date')
        
        print(f"   Günlük event dağılımı (ilk 10 gün):")
        for row in daily_events.head(10).iter_rows():
            date, count = row
            print(f"   {date}: {count:,} events")
        
        # Saatlik dağılım (ilk gün için)
        first_date = daily_events.head(1).select('date').item()
        hourly_events = df_with_date.filter(
            pl.col('event_datetime').dt.date() == first_date
        ).group_by(
            pl.col('event_datetime').dt.hour().alias('hour')
        ).agg([
            pl.len().alias('event_count')
        ]).sort('hour')
        
        print(f"\n   Saatlik dağılım ({first_date}):")
        for row in hourly_events.iter_rows():
            hour, count = row
            print(f"   {hour:02d}:00 - {count:,} events")
    
    # Event time ile event_name ilişkisi
    print(f"\n🔗 EVENT TIME vs EVENT NAME İLİŞKİSİ:")
    
    # Her event type için ortalama time
    event_time_stats = df.group_by('event_name').agg([
        pl.col('event_time').mean().alias('avg_time'),
        pl.col('event_time').min().alias('min_time'),
        pl.col('event_time').max().alias('max_time'),
        pl.len().alias('count')
    ]).sort('count', descending=True)
    
    for row in event_time_stats.iter_rows():
        event_name, avg_time, min_time, max_time, count = row
        print(f"   {event_name}:")
        print(f"     Count: {count:,}")
        print(f"     Avg time: {avg_time}")
        print(f"     Time range: {max_time - min_time}")
        print()
    
    # Kullanım amacı analizi
    print(f"\n🎯 EVENT TIME KULLANIM AMACI:")
    print("=" * 40)
    print("   1. 📅 Temporal Pattern Analysis")
    print("      - Günlük/saatlik kullanım patternleri")
    print("      - Peak usage saatleri")
    print("      - Seasonal trends")
    print()
    print("   2. ⏱️  User Journey Tracking")
    print("      - Event sequence timing")
    print("      - Conversion funnel timing")
    print("      - Session duration")
    print()
    print("   3. 🔄 Feature Engineering")
    print("      - Time-based features (hour, day, month)")
    print("      - Time since first event")
    print("      - Event frequency over time")
    print()
    print("   4. 📊 Cohort Analysis")
    print("      - User acquisition date")
    print("      - Retention analysis")
    print("      - Churn prediction")

if __name__ == "__main__":
    analyze_event_time()
