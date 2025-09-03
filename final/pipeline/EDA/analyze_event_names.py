import polars as pl
from collections import Counter

def analyze_event_names():
    """event_name sütunundaki class'ları ve mapping'lerini analiz eder"""
    print("🔍 Event Name Class Analizi...")
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    print(f"📊 Toplam satır: {len(df):,}")
    
    # Event name'leri analiz et
    event_counts = df.group_by('event_name').agg([
        pl.len().alias('count'),
        pl.col('revenue').sum().alias('total_revenue'),
        pl.col('revenue').mean().alias('avg_revenue'),
        pl.col('user_id').n_unique().alias('unique_users')
    ]).sort('count', descending=True)
    
    print(f"\n📊 Event Name Class'ları ({len(event_counts)} adet):")
    print("=" * 80)
    
    # Her event için detaylı analiz
    for i, row in enumerate(event_counts.iter_rows()):
        event_name, count, total_revenue, avg_revenue, unique_users = row
        
        # Event'in revenue potansiyelini değerlendir
        avg_revenue_safe = avg_revenue if avg_revenue is not None else 0.0
        total_revenue_safe = total_revenue if total_revenue is not None else 0.0
        
        revenue_potential = "💰" if avg_revenue_safe > 0 else "📊"
        user_penetration = (unique_users / df['user_id'].n_unique()) * 100
        
        print(f"{i+1:2d}. {revenue_potential} {event_name}")
        print(f"     📈 Count: {count:,} events")
        print(f"     👥 Unique Users: {unique_users:,} ({user_penetration:.2f}% of total users)")
        print(f"     💰 Total Revenue: ${total_revenue_safe:,.2f}")
        print(f"     💵 Avg Revenue per Event: ${avg_revenue_safe:.4f}")
        print()
    
    # Event kategorilerini belirle
    print("🏷️  EVENT KATEGORİLERİ:")
    print("=" * 50)
    
    # Revenue-generating events
    revenue_events = event_counts.filter(pl.col('avg_revenue').is_not_null() & (pl.col('avg_revenue') > 0))
    print(f"\n💰 REVENUE-GENERATING EVENTS ({len(revenue_events)} adet):")
    for row in revenue_events.iter_rows():
        event_name, count, total_revenue, avg_revenue, unique_users = row
        avg_revenue_safe = avg_revenue if avg_revenue is not None else 0.0
        print(f"   • {event_name}: ${avg_revenue_safe:.4f} avg revenue")
    
    # Non-revenue events
    non_revenue_events = event_counts.filter(pl.col('avg_revenue').is_null() | (pl.col('avg_revenue') == 0))
    print(f"\n📊 NON-REVENUE EVENTS ({len(non_revenue_events)} adet):")
    for row in non_revenue_events.iter_rows():
        event_name, count, total_revenue, avg_revenue, unique_users = row
        print(f"   • {event_name}: {count:,} events")
    
    # Event frequency analizi
    print(f"\n📈 EVENT FREQUENCY ANALİZİ:")
    print("=" * 40)
    
    total_events = len(df)
    for row in event_counts.iter_rows():
        event_name, count, total_revenue, avg_revenue, unique_users = row
        percentage = (count / total_events) * 100
        print(f"   {event_name}: {percentage:.2f}% ({count:,} events)")
    
    # Event mapping önerisi
    print(f"\n🗺️  EVENT MAPPING ÖNERİSİ:")
    print("=" * 40)
    
    event_mapping = {}
    for row in event_counts.iter_rows():
        event_name, count, total_revenue, avg_revenue, unique_users = row
        
        # Event tipini belirle
        avg_revenue_safe = avg_revenue if avg_revenue is not None else 0.0
        if avg_revenue_safe > 0:
            if 'purchase' in event_name.lower() or 'payment' in event_name.lower():
                event_type = 'PURCHASE'
            elif 'subscription' in event_name.lower():
                event_type = 'SUBSCRIPTION'
            else:
                event_type = 'REVENUE'
        else:
            if 'view' in event_name.lower() or 'show' in event_name.lower():
                event_type = 'VIEW'
            elif 'click' in event_name.lower():
                event_type = 'CLICK'
            elif 'start' in event_name.lower() or 'begin' in event_name.lower():
                event_type = 'START'
            elif 'complete' in event_name.lower() or 'finish' in event_name.lower():
                event_type = 'COMPLETE'
            else:
                event_type = 'ENGAGEMENT'
        
        event_mapping[event_name] = event_type
        print(f"   '{event_name}' → {event_type}")
    
    # Mapping'i dosyaya kaydet
    with open('event_name_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("EVENT NAME MAPPING\n")
        f.write("=" * 50 + "\n\n")
        for event_name, event_type in event_mapping.items():
            f.write(f"'{event_name}' → {event_type}\n")
    
    print(f"\n💾 Event mapping 'event_name_mapping.txt' dosyasına kaydedildi!")
    
    return event_mapping

if __name__ == "__main__":
    analyze_event_names()
