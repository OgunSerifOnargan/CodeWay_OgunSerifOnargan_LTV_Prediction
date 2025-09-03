import polars as pl
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def create_revenue_features_table():
    """Revenue features tablosunu oluştur"""
    print("🗄️ Revenue Features Tablosu Oluşturuluyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    with engine.connect() as conn:
        # Tabloyu sil (eğer varsa)
        conn.execute(text("DROP TABLE IF EXISTS revenue_features"))
        conn.commit()
        
        # Yeni tablo oluştur
        create_table_sql = """
        CREATE TABLE test_revenue_features (
            user_id VARCHAR(50) PRIMARY KEY,
            
            -- Core Revenue Metrics (3 features)
            first_15_days_total_revenue DECIMAL(10,2) DEFAULT 0.0,
            first_15_days_avg_revenue_per_event DECIMAL(10,2) DEFAULT 0.0,
            first_15_days_revenue_per_day DECIMAL(10,2) DEFAULT 0.0,
            
            -- Revenue Risk Metrics (8 features)
            has_refund_in_first_15_days INTEGER DEFAULT 0,
            refund_amount_in_first_15_days DECIMAL(10,2) DEFAULT 0.0,
            refund_ratio_in_first_15_days DECIMAL(8,4) DEFAULT 0.0,
            revenue_volatility_in_first_15_days DECIMAL(10,4) DEFAULT 0.0,
            revenue_efficiency_in_first_15_days DECIMAL(10,4) DEFAULT 0.0,
            days_to_first_revenue INTEGER DEFAULT NULL,
            revenue_concentration_in_first_15_days DECIMAL(8,4) DEFAULT 0.0,
            revenue_pattern_risk_in_first_15_days INTEGER DEFAULT 0
        );
        """
        
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✅ Revenue features tablosu oluşturuldu!")

def calculate_revenue_features_for_user_batch(user_batch_data):
    """User batch için revenue features hesapla"""
    features_list = []
    
    for user_id, user_data in user_batch_data:
        try:
            # İlk event tarihini al
            first_event_date = user_data.select('first_event_date').head(1).item()
            first_event_datetime = datetime.strptime(first_event_date, '%Y-%m-%d')
            end_date = first_event_datetime + pd.Timedelta(days=15)
            
            # İlk 15 günlük event'leri filtrele
            first_15_days_events = user_data.with_columns([
                pl.col('event_time').cast(pl.Int64).map_elements(
                    lambda x: datetime.fromtimestamp(x / 1000) if x else None,
                    return_dtype=pl.Object
                ).alias('event_datetime')
            ])
            
            # İlk 15 günlük event'leri filtrele
            filtered_events = []
            for row in first_15_days_events.iter_rows(named=True):
                event_dt = row['event_datetime']
                if event_dt and first_event_datetime <= event_dt < end_date:
                    filtered_events.append(row)
            
            if not filtered_events:
                continue
            
            # Core Revenue Metrics
            total_revenue = sum(row['revenue'] or 0 for row in filtered_events)
            total_events = len(filtered_events)
            avg_revenue_per_event = total_revenue / total_events if total_events > 0 else 0.0
            revenue_per_day = total_revenue / 15.0
            
            # Revenue Risk Metrics
            refund_events = [row for row in filtered_events if row['event_name'] == 'refund']
            has_refund = 1 if refund_events else 0
            refund_amount = sum(row['revenue'] or 0 for row in refund_events)
            
            # Refund ratio (sadece positive revenue olan user'lar için)
            refund_ratio = 0.0
            if total_revenue > 0:
                refund_ratio = abs(refund_amount) / total_revenue
            
            # Revenue volatility (günlük revenue standard deviation)
            daily_revenue = {}
            for row in filtered_events:
                event_date = row['event_datetime'].date()
                daily_revenue[event_date] = daily_revenue.get(event_date, 0) + (row['revenue'] or 0)
            
            revenue_volatility = np.std(list(daily_revenue.values())) if len(daily_revenue) > 1 else 0.0
            
            # Revenue efficiency (revenue / conversion events)
            conversion_events = [row for row in filtered_events if row['event_name'] in ['subscribe', 'renewal']]
            revenue_efficiency = total_revenue / len(conversion_events) if conversion_events else 0.0
            
            # Days to first revenue
            revenue_events = [row for row in filtered_events if (row['revenue'] or 0) > 0]
            days_to_first_revenue = None
            if revenue_events:
                first_revenue_event = min(revenue_events, key=lambda x: x['event_datetime'])
                days_to_first_revenue = (first_revenue_event['event_datetime'] - first_event_datetime).days
            
            # Revenue concentration (max single day revenue / total revenue)
            revenue_concentration = 0.0
            if total_revenue > 0 and daily_revenue:
                max_daily_revenue = max(daily_revenue.values())
                revenue_concentration = max_daily_revenue / total_revenue
            
            # Revenue pattern risk (1 if revenue declines over time, 0 if stable/increasing)
            revenue_pattern_risk = 0
            if len(daily_revenue) > 2:
                daily_revenue_list = sorted(daily_revenue.items())
                first_half = sum(rev for _, rev in daily_revenue_list[:len(daily_revenue_list)//2])
                second_half = sum(rev for _, rev in daily_revenue_list[len(daily_revenue_list)//2:])
                if second_half < first_half:
                    revenue_pattern_risk = 1
            
            features_list.append({
                'user_id': user_id,
                'first_15_days_total_revenue': total_revenue,
                'first_15_days_avg_revenue_per_event': avg_revenue_per_event,
                'first_15_days_revenue_per_day': revenue_per_day,
                'has_refund_in_first_15_days': has_refund,
                'refund_amount_in_first_15_days': refund_amount,
                'refund_ratio_in_first_15_days': refund_ratio,
                'revenue_volatility_in_first_15_days': revenue_volatility,
                'revenue_efficiency_in_first_15_days': revenue_efficiency,
                'days_to_first_revenue': days_to_first_revenue,
                'revenue_concentration_in_first_15_days': revenue_concentration,
                'revenue_pattern_risk_in_first_15_days': revenue_pattern_risk
            })
            
        except Exception as e:
            continue
    
    return features_list

def process_chunk_parallel(chunk_data, chunk_id, total_chunks):
    """Chunk'ı paralel olarak işle"""
    try:
        # User'ları grupla
        user_groups = {}
        for row in chunk_data.iter_rows(named=True):
            user_id = row['user_id']
            if user_id not in user_groups:
                user_groups[user_id] = []
            user_groups[user_id].append(row)
        
        # User batch'lerini oluştur
        user_batch = []
        for user_id, user_rows in user_groups.items():
            user_df = pl.DataFrame(user_rows)
            user_batch.append((user_id, user_df))
        
        # Revenue features hesapla
        features_list = calculate_revenue_features_for_user_batch(user_batch)
        
        if features_list:
            # Database'e kaydet
            engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
            features_df = pd.DataFrame(features_list)
            
            with engine.connect() as conn:
                features_df.to_sql('test_revenue_features', conn, if_exists='append', index=False, method='multi')
                conn.commit()
        
        return len(features_list)
        
    except Exception as e:
        return 0

def process_revenue_features_parallel():
    """Revenue features'ları paralel olarak işle"""
    print("🔄 Revenue Features Paralel İşleniyor...")
    
    # Raw dataset'ten veri çek
    df = pl.read_parquet('ltvprediction_case.parquet')
    unique_users = df.select('user_id').unique().sort('user_id')
    total_users = len(unique_users)
    
    print(f"📊 Toplam {total_users:,} user işlenecek")
    
    # Chunk boyutu
    chunk_size = 5000  # 5K user per chunk
    total_chunks = (total_users + chunk_size - 1) // chunk_size
    
    # Thread sayısı
    max_workers = 20
    print(f"🧵 {max_workers} thread ile {total_chunks} chunk işlenecek")
    
    start_time = time.time()
    
    # ThreadPoolExecutor ile paralel işlem
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        # Chunk'ları oluştur ve submit et
        for chunk_idx in tqdm(range(total_chunks), desc="Chunk'lar Hazırlanıyor"):
            start_idx = chunk_idx * chunk_size
            end_idx = min((chunk_idx + 1) * chunk_size, total_users)
            
            chunk_users = unique_users.slice(start_idx, end_idx - start_idx)
            user_ids = chunk_users.select('user_id').to_series().to_list()
            
            chunk_data = df.filter(pl.col('user_id').is_in(user_ids))
            
            # Future'ı submit et
            future = executor.submit(process_chunk_parallel, chunk_data, chunk_idx, total_chunks)
            futures.append(future)
        
        # Progress bar ile sonuçları bekle
        processed_count = 0
        successful_chunks = 0
        
        with tqdm(total=total_chunks, desc="Chunk İşleniyor", unit="chunk") as pbar:
            for future in as_completed(futures):
                try:
                    result = future.result()
                    processed_count += result
                    successful_chunks += 1
                    pbar.set_postfix({
                        'İşlenen': f"{processed_count:,}",
                        'Başarılı': f"{successful_chunks}/{total_chunks}"
                    })
                    pbar.update(1)
                except Exception as e:
                    pbar.update(1)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"\n🎉 Paralel İşlem Tamamlandı!")
    print(f"⏱️  Toplam süre: {processing_time:.2f} saniye")
    print(f"✅ İşlenen user: {processed_count:,}")
    print(f"✅ Başarılı chunk: {successful_chunks}/{total_chunks}")

def verify_revenue_features():
    """Revenue features'ı doğrula"""
    print("\n🔍 Revenue Features Doğrulanıyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    with engine.connect() as conn:
        # Toplam kayıt sayısı
        total_count = pd.read_sql("SELECT COUNT(*) as total FROM revenue_features", conn)
        print(f"📊 Toplam kayıt: {total_count['total'].iloc[0]:,}")
        
        # Örnek kayıtlar
        sample_data = pd.read_sql("SELECT * FROM revenue_features LIMIT 5", conn)
        print("\n📋 Örnek Kayıtlar:")
        print(sample_data)
        
        # İstatistikler
        stats_query = """
        SELECT 
            AVG(first_15_days_total_revenue) as avg_total_revenue,
            AVG(first_15_days_avg_revenue_per_event) as avg_revenue_per_event,
            SUM(has_refund_in_first_15_days) as total_refund_users,
            AVG(refund_ratio_in_first_15_days) as avg_refund_ratio,
            AVG(revenue_volatility_in_first_15_days) as avg_volatility
        FROM revenue_features
        """
        stats = pd.read_sql(stats_query, conn)
        print("\n📊 İstatistikler:")
        print(stats)

def create_revenue_indexes():
    """Revenue features için index'ler oluştur"""
    print("\n📊 Revenue Index'ler Oluşturuluyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    with engine.connect() as conn:
        # Index'ler oluştur
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_revenue_total ON revenue_features(first_15_days_total_revenue)",
            "CREATE INDEX IF NOT EXISTS idx_revenue_refund ON revenue_features(has_refund_in_first_15_days)",
            "CREATE INDEX IF NOT EXISTS idx_revenue_volatility ON revenue_features(revenue_volatility_in_first_15_days)",
            "CREATE INDEX IF NOT EXISTS idx_revenue_efficiency ON revenue_features(revenue_efficiency_in_first_15_days)"
        ]
        
        for index_sql in indexes:
            conn.execute(text(index_sql))
        
        conn.commit()
    
    print("✅ Revenue index'ler oluşturuldu!")

def main():
    """Ana fonksiyon"""
    print("💰 REVENUE FEATURES PARALEL OLUŞTURMA")
    print("=" * 80)
    
    # 1. Tablo oluştur
    create_revenue_features_table()
    
    # 2. Paralel işlem
    process_revenue_features_parallel()
    
    # 3. Doğrula
    verify_revenue_features()
    
    # 4. Index'ler oluştur
    create_revenue_indexes()
    
    print(f"\n🎉 REVENUE FEATURES BAŞARIYLA OLUŞTURULDU!")
    print(f"✅ Core revenue metrics (3 feature)")
    print(f"✅ Revenue risk metrics (8 feature)")
    print(f"✅ Paralel processing ile hızlı işlem")
    print(f"✅ Index'ler oluşturuldu")

if __name__ == "__main__":
    main()
