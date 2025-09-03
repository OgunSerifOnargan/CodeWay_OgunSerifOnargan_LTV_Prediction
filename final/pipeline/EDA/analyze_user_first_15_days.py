import polars as pl
from datetime import datetime, timedelta

def analyze_user_first_15_days():
    """Her user'ın ilk 15 günlük engagement'ını analiz eder"""
    print("🔍 User İlk 15 Günlük Engagement Analizi...")
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    print(f"📊 Toplam satır: {len(df):,}")
    print(f"📊 Unique user sayısı: {df['user_id'].n_unique():,}")
    
    # Event time'i datetime'a çevir
    df_with_date = df.with_columns([
        pl.col('event_time').cast(pl.Int64).map_elements(
            lambda x: datetime.fromtimestamp(x / 1000) if x else None
        ).alias('event_datetime')
    ])
    
    # Her user için ilk event tarihini bul
    print(f"\n📅 USER İLK EVENT ANALİZİ:")
    user_first_events = df_with_date.group_by('user_id').agg([
        pl.col('event_datetime').min().alias('first_event_date'),
        pl.col('event_datetime').max().alias('last_event_date'),
        pl.len().alias('total_events')
    ]).sort('first_event_date')
    
    print(f"   Toplam user sayısı: {len(user_first_events):,}")
    
    # İlk event tarihlerinin dağılımı
    print(f"\n📈 İLK EVENT TARİH DAĞILIMI:")
    
    # Günlük user acquisition
    daily_acquisition = user_first_events.group_by(
        pl.col('first_event_date').dt.date().alias('acquisition_date')
    ).agg([
        pl.len().alias('new_users'),
        pl.col('total_events').mean().alias('avg_events_per_user')
    ]).sort('acquisition_date')
    
    print(f"   Toplam acquisition günü: {len(daily_acquisition)}")
    
    # İlk 10 günü göster
    print(f"\n   İlk 10 gün user acquisition:")
    for row in daily_acquisition.head(10).iter_rows():
        date, users, avg_events = row
        print(f"   {date}: {users:,} yeni user, {avg_events:.1f} avg events")
    
    # Son 10 günü göster
    print(f"\n   Son 10 gün user acquisition:")
    for row in daily_acquisition.tail(10).iter_rows():
        date, users, avg_events = row
        print(f"   {date}: {users:,} yeni user, {avg_events:.1f} avg events")
    
    # 15 günlük engagement analizi
    print(f"\n🔍 15 GÜNLÜK ENGAGEMENT ANALİZİ:")
    
    # Her user için ilk 15 günlük event'leri hesapla
    user_15_day_events = []
    
    for row in user_first_events.iter_rows():
        user_id, first_date, last_date, total_events = row
        
        if first_date:
            # İlk 15 günün bitiş tarihi
            end_15_days = first_date + timedelta(days=15)
            
            # Bu user'ın ilk 15 günündeki event'leri say
            user_events_15_days = df_with_date.filter(
                (pl.col('user_id') == user_id) & 
                (pl.col('event_datetime') >= first_date) & 
                (pl.col('event_datetime') < end_15_days)
            )
            
            events_15_days = len(user_events_15_days)
            user_15_day_events.append((user_id, first_date, events_15_days, total_events))
    
    # 15 günlük engagement istatistikleri
    events_15_days_list = [events for _, _, events, _ in user_15_day_events]
    
    print(f"   Ortalama 15 günlük event: {sum(events_15_days_list)/len(events_15_days_list):.1f}")
    print(f"   En yüksek 15 günlük event: {max(events_15_days_list)}")
    print(f"   En düşük 15 günlük event: {min(events_15_days_list)}")
    
    # 15 günlük engagement dağılımı
    print(f"\n📊 15 GÜNLÜK ENGAGEMENT DAĞILIMI:")
    
    # Engagement kategorileri
    low_engagement = sum(1 for events in events_15_days_list if events <= 10)
    medium_engagement = sum(1 for events in events_15_days_list if 11 <= events <= 50)
    high_engagement = sum(1 for events in events_15_days_list if events > 50)
    
    print(f"   Düşük engagement (≤10 events): {low_engagement:,} user ({low_engagement/len(events_15_days_list)*100:.1f}%)")
    print(f"   Orta engagement (11-50 events): {medium_engagement:,} user ({medium_engagement/len(events_15_days_list)*100:.1f}%)")
    print(f"   Yüksek engagement (>50 events): {high_engagement:,} user ({high_engagement/len(events_15_days_list)*100:.1f}%)")
    
    # İlk 15 günlük event type dağılımı
    print(f"\n🎯 İLK 15 GÜNLÜK EVENT TYPE DAĞILIMI:")
    
    # Tüm user'ların ilk 15 günlük event'lerini topla
    all_15_day_events = []
    for user_id, first_date, _, _ in user_15_day_events:
        end_15_days = first_date + timedelta(days=15)
        user_events = df_with_date.filter(
            (pl.col('user_id') == user_id) & 
            (pl.col('event_datetime') >= first_date) & 
            (pl.col('event_datetime') < end_15_days)
        )
        all_15_day_events.append(user_events)
    
    if all_15_day_events:
        combined_15_day_events = pl.concat(all_15_day_events)
        
        # Event type dağılımı
        event_type_dist = combined_15_day_events.group_by('event_name').agg([
            pl.len().alias('count'),
            pl.col('user_id').n_unique().alias('unique_users')
        ]).sort('count', descending=True)
        
        print(f"   İlk 15 günlük toplam event: {len(combined_15_day_events):,}")
        print(f"   İlk 15 günlük unique user: {combined_15_day_events['user_id'].n_unique():,}")
        
        for row in event_type_dist.iter_rows():
            event_name, count, users = row
            print(f"   {event_name}: {count:,} events, {users:,} users")
    
    # User journey analizi (ilk 15 gün)
    print(f"\n🔄 İLK 15 GÜNLÜK USER JOURNEY:")
    
    # İlk 15 gününde conversion yapan user'lar
    conversion_users_15_days = []
    
    for user_id, first_date, events_15_days, total_events in user_15_day_events[:100]:  # İlk 100 user
        end_15_days = first_date + timedelta(days=15)
        
        user_events = df_with_date.filter(
            (pl.col('user_id') == user_id) & 
            (pl.col('event_datetime') >= first_date) & 
            (pl.col('event_datetime') < end_15_days)
        )
        
        # Event sequence'i al
        event_sequence = user_events.select(['event_datetime', 'event_name']).sort('event_datetime')
        
        # Conversion events var mı?
        has_trial = any(event_sequence['event_name'].to_list() == 'free_trial')
        has_subscribe = any(event_sequence['event_name'].to_list() == 'subscribe')
        has_renewal = any(event_sequence['event_name'].to_list() == 'renewal')
        
        if has_trial or has_subscribe or has_renewal:
            conversion_users_15_days.append((user_id, has_trial, has_subscribe, has_renewal, events_15_days))
    
    print(f"   İlk 100 user'dan conversion yapanlar:")
    trial_users = sum(1 for _, has_trial, _, _, _ in conversion_users_15_days if has_trial)
    subscribe_users = sum(1 for _, _, has_subscribe, _, _ in conversion_users_15_days if has_subscribe)
    renewal_users = sum(1 for _, _, _, has_renewal, _ in conversion_users_15_days if has_renewal)
    
    print(f"   Free trial: {trial_users} user")
    print(f"   Subscribe: {subscribe_users} user")
    print(f"   Renewal: {renewal_users} user")
    
    # Veri setinin 15 günlük engagement için uygunluğu
    print(f"\n✅ VERİ SETİ UYGUNLUK KONTROLÜ:")
    
    # Tüm user'ların ilk 15 günü veri setinde mi?
    all_users_have_15_days = True
    users_without_15_days = 0
    
    for user_id, first_date, _, _ in user_15_day_events:
        end_15_days = first_date + timedelta(days=15)
        last_available_date = df_with_date.select('event_datetime').max().item()
        
        if end_15_days > last_available_date:
            all_users_have_15_days = False
            users_without_15_days += 1
    
    if all_users_have_15_days:
        print(f"   ✅ Tüm user'ların ilk 15 günü veri setinde mevcut")
    else:
        print(f"   ⚠️  {users_without_15_days:,} user'ın ilk 15 günü veri setinde eksik")
        print(f"   📊 Bu user'lar için kısmi veri kullanılabilir")

if __name__ == "__main__":
    analyze_user_first_15_days()
