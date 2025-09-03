import polars as pl
from datetime import datetime, timedelta

def check_data_timespan():
    """Verinin gerçek zaman aralığını kontrol eder"""
    print("🔍 Veri Zaman Aralığı Kontrolü...")
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    print(f"📊 Toplam satır: {len(df):,}")
    
    # Event time'i datetime'a çevir
    df_with_date = df.with_columns([
        pl.col('event_time').cast(pl.Int64).map_elements(
            lambda x: datetime.fromtimestamp(x / 1000) if x else None
        ).alias('event_datetime')
    ])
    
    # Min, max tarihleri
    min_date = df_with_date.select('event_datetime').min().item()
    max_date = df_with_date.select('event_datetime').max().item()
    
    print(f"\n📅 ZAMAN ARALIĞI:")
    print(f"   En erken event: {min_date}")
    print(f"   En geç event: {max_date}")
    
    # Toplam süreyi hesapla
    total_duration = max_date - min_date
    print(f"   Toplam süre: {total_duration}")
    print(f"   Toplam gün: {total_duration.days}")
    
    # Günlük event sayılarını kontrol et
    print(f"\n📈 GÜNLÜK EVENT DAĞILIMI:")
    daily_events = df_with_date.group_by(
        pl.col('event_datetime').dt.date().alias('date')
    ).agg([
        pl.len().alias('event_count'),
        pl.col('user_id').n_unique().alias('unique_users')
    ]).sort('date')
    
    print(f"   Toplam gün sayısı: {len(daily_events)}")
    print(f"   Ortalama günlük event: {daily_events.select('event_count').mean().item():,.0f}")
    
    # İlk 10 günü göster
    print(f"\n   İlk 10 gün:")
    for row in daily_events.head(10).iter_rows():
        date, count, users = row
        print(f"   {date}: {count:,} events, {users:,} users")
    
    # Son 10 günü göster
    print(f"\n   Son 10 gün:")
    for row in daily_events.tail(10).iter_rows():
        date, count, users = row
        print(f"   {date}: {count:,} events, {users:,} users")
    
    # 15 günlük veri kontrolü
    print(f"\n🔍 15 GÜNLÜK VERİ KONTROLÜ:")
    
    if total_duration.days <= 15:
        print(f"   ✅ Veri 15 günlük veya daha az: {total_duration.days} gün")
    else:
        print(f"   ❌ Veri 15 günden fazla: {total_duration.days} gün")
        print(f"   ⚠️  Beklenen: 15 gün, Gerçek: {total_duration.days} gün")
    
    # Event yoğunluğu analizi
    print(f"\n📊 EVENT YOĞUNLUĞU ANALİZİ:")
    
    # En yoğun günler
    top_days = daily_events.sort('event_count', descending=True).head(5)
    print(f"   En yoğun 5 gün:")
    for row in top_days.iter_rows():
        date, count, users = row
        print(f"   {date}: {count:,} events")
    
    # En az yoğun günler
    low_days = daily_events.sort('event_count').head(5)
    print(f"\n   En az yoğun 5 gün:")
    for row in low_days.iter_rows():
        date, count, users = row
        print(f"   {date}: {count:,} events")
    
    # Veri kalitesi kontrolü
    print(f"\n🔍 VERİ KALİTESİ KONTROLÜ:")
    
    # Null event_time kontrolü
    null_times = df.filter(pl.col('event_time').is_null()).height
    print(f"   Null event_time sayısı: {null_times}")
    
    # Geçersiz timestamp kontrolü
    invalid_times = df.filter(pl.col('event_time') < 1000000000000).height
    print(f"   Geçersiz timestamp sayısı: {invalid_times}")
    
    # User bazında zaman aralığı
    print(f"\n👥 USER BAZINDA ZAMAN ARALIĞI:")
    user_time_ranges = df_with_date.group_by('user_id').agg([
        pl.col('event_datetime').min().alias('first_event'),
        pl.col('event_datetime').max().alias('last_event'),
        pl.len().alias('event_count')
    ])
    
    # User'ların aktivite süreleri
    user_durations = []
    for row in user_time_ranges.iter_rows():
        user_id, first_event, last_event, count = row
        if first_event and last_event:
            duration = (last_event - first_event).days
            user_durations.append(duration)
    
    if user_durations:
        avg_user_duration = sum(user_durations) / len(user_durations)
        max_user_duration = max(user_durations)
        min_user_duration = min(user_durations)
        
        print(f"   Ortalama user aktivite süresi: {avg_user_duration:.1f} gün")
        print(f"   En uzun user aktivite süresi: {max_user_duration} gün")
        print(f"   En kısa user aktivite süresi: {min_user_duration} gün")

if __name__ == "__main__":
    check_data_timespan()
