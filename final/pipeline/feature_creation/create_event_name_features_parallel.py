import polars as pl
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
from datetime import datetime
import numpy as np
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import time

def create_event_name_features_table():
    """Event name features tablosunu oluştur"""
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Önce tabloyu sil
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS event_name_features"))
        conn.commit()
    
    create_table_sql = """
    CREATE TABLE test_event_name_features (
        user_id VARCHAR(50) PRIMARY KEY,
        
        -- Revenue Features (TIER 1 - En Kritik)
        first_15_days_total_revenue DECIMAL(10,2) DEFAULT 0.0,
        first_15_days_avg_revenue_per_event DECIMAL(10,2) DEFAULT 0.0,
        first_15_days_revenue_per_day DECIMAL(10,2) DEFAULT 0.0,
        has_revenue_in_first_15_days INTEGER DEFAULT 0,
        
        -- Event Count Features
        first_15_days_subscribe_count INTEGER DEFAULT 0,
        first_15_days_renewal_count INTEGER DEFAULT 0,
        first_15_days_revenue_events_total INTEGER DEFAULT 0,
        first_15_days_total_events INTEGER DEFAULT 0,
        
        -- Binary Conversion Features
        has_subscribe_in_first_15_days INTEGER DEFAULT 0,
        has_renewal_in_first_15_days INTEGER DEFAULT 0,
        has_trial_in_first_15_days INTEGER DEFAULT 0,
        has_refund_in_first_15_days INTEGER DEFAULT 0,
        has_auto_renew_off_in_first_15_days INTEGER DEFAULT 0,
        
        -- Timing Features
        days_to_first_subscribe INTEGER DEFAULT NULL,
        days_to_first_renewal INTEGER DEFAULT NULL,
        conversion_velocity INTEGER DEFAULT NULL,
        
        -- Engagement Features
        first_15_days_active_days INTEGER DEFAULT 0,
        first_15_days_event_diversity INTEGER DEFAULT 0
    );
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()

def calculate_event_name_features_for_user_batch(user_batch_data):
    """Bir batch user için event name feature'larını hesapla"""
    features_list = []
    
    for user_id, user_data in user_batch_data:
        try:
            # İlk event tarihini al
            first_event_date = user_data.select('first_event_date').head(1).item()
            first_event_datetime = datetime.strptime(first_event_date, '%Y-%m-%d')
            
            # İlk 15 günlük window hesapla
            end_date = first_event_datetime + pd.Timedelta(days=15)
            
            # İlk 15 günlük event'leri filtrele
            first_15_days_events = user_data.with_columns([
                pl.col('event_time').cast(pl.Int64).map_elements(
                    lambda x: datetime.fromtimestamp(x / 1000) if x else None,
                    return_dtype=pl.Object
                ).alias('event_datetime')
            ])
            
            # Python tarafında filtrele
            filtered_events = []
            for row in first_15_days_events.iter_rows(named=True):
                event_dt = row['event_datetime']
                if event_dt and first_event_datetime <= event_dt < end_date:
                    filtered_events.append(row)
            
            if not filtered_events:
                continue
            
            # Revenue Features
            total_revenue = sum(row['revenue'] or 0 for row in filtered_events)
            avg_revenue_per_event = total_revenue / len(filtered_events) if filtered_events else 0.0
            revenue_per_day = total_revenue / 15.0
            has_revenue = 1 if total_revenue > 0 else 0
            
            # Event Counts
            subscribe_count = sum(1 for row in filtered_events if row['event_name'] == 'subscribe')
            renewal_count = sum(1 for row in filtered_events if row['event_name'] == 'renewal')
            revenue_events_total = subscribe_count + renewal_count
            total_events = len(filtered_events)
            
            # Binary Features
            has_subscribe = 1 if subscribe_count > 0 else 0
            has_renewal = 1 if renewal_count > 0 else 0
            has_trial = 1 if any(row['event_name'] == 'free_trial' for row in filtered_events) else 0
            has_refund = 1 if any(row['event_name'] == 'refund' for row in filtered_events) else 0
            has_auto_renew_off = 1 if any(row['event_name'] == 'auto_renew_off' for row in filtered_events) else 0
            
            # Timing Features
            days_to_first_subscribe = None
            days_to_first_renewal = None
            conversion_velocity = None
            
            if has_subscribe:
                subscribe_events = [row for row in filtered_events if row['event_name'] == 'subscribe']
                if subscribe_events:
                    first_subscribe = min(subscribe_events, key=lambda x: x['event_datetime'])
                    days_to_first_subscribe = (first_subscribe['event_datetime'] - first_event_datetime).days
            
            if has_renewal:
                renewal_events = [row for row in filtered_events if row['event_name'] == 'renewal']
                if renewal_events:
                    first_renewal = min(renewal_events, key=lambda x: x['event_datetime'])
                    days_to_first_renewal = (first_renewal['event_datetime'] - first_event_datetime).days
            
            # Conversion velocity
            if has_subscribe:
                conversion_velocity = days_to_first_subscribe
            elif has_renewal:
                conversion_velocity = days_to_first_renewal
            
            # Engagement Features
            active_days = len(set(row['event_datetime'].date() for row in filtered_events if row['event_datetime']))
            event_diversity = len(set(row['event_name'] for row in filtered_events))
            
            features_list.append({
                'user_id': user_id,
                'first_15_days_total_revenue': total_revenue,
                'first_15_days_avg_revenue_per_event': avg_revenue_per_event,
                'first_15_days_revenue_per_day': revenue_per_day,
                'has_revenue_in_first_15_days': has_revenue,
                'first_15_days_subscribe_count': subscribe_count,
                'first_15_days_renewal_count': renewal_count,
                'first_15_days_revenue_events_total': revenue_events_total,
                'first_15_days_total_events': total_events,
                'has_subscribe_in_first_15_days': has_subscribe,
                'has_renewal_in_first_15_days': has_renewal,
                'has_trial_in_first_15_days': has_trial,
                'has_refund_in_first_15_days': has_refund,
                'has_auto_renew_off_in_first_15_days': has_auto_renew_off,
                'days_to_first_subscribe': days_to_first_subscribe,
                'days_to_first_renewal': days_to_first_renewal,
                'conversion_velocity': conversion_velocity,
                'first_15_days_active_days': active_days,
                'first_15_days_event_diversity': event_diversity
            })
            
        except Exception as e:
            continue
    
    return features_list

def process_chunk_parallel(chunk_data, chunk_id, total_chunks):
    """Bir chunk'ı paralel işle"""
    try:
        # User bazında grupla
        user_groups = {}
        for row in chunk_data.iter_rows(named=True):
            user_id = row['user_id']
            if user_id not in user_groups:
                user_groups[user_id] = []
            user_groups[user_id].append(row)
        
        # Her user için Polars DataFrame oluştur
        user_batch = []
        for user_id, user_rows in user_groups.items():
            user_df = pl.DataFrame(user_rows)
            user_batch.append((user_id, user_df))
        
        # Feature'ları hesapla
        features_list = calculate_event_name_features_for_user_batch(user_batch)
        
        # Database'e kaydet
        if features_list:
            engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
            features_df = pd.DataFrame(features_list)
            
            with engine.connect() as conn:
                features_df.to_sql('test_event_name_features', conn, if_exists='append', index=False, method='multi')
                conn.commit()
        
        return len(features_list)
        
    except Exception as e:
        return 0

def process_event_name_features_parallel():
    """Event name feature'larını paralel işle"""
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    # Unique user'ları al
    unique_users = df.select('user_id').unique().sort('user_id')
    total_users = len(unique_users)
    
    # Chunk size - daha büyük chunk'lar
    chunk_size = 5000  # 5K user per chunk
    total_chunks = (total_users + chunk_size - 1) // chunk_size
    
    # Thread sayısı
    max_workers = 50  # 50 thread paralel
    
    start_time = time.time()
    
    # ThreadPoolExecutor ile paralel işlem
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Future'ları topla
        futures = []
        
        for chunk_idx in range(total_chunks):
            start_idx = chunk_idx * chunk_size
            end_idx = min((chunk_idx + 1) * chunk_size, total_users)
            
            # Bu chunk'taki user'ları al
            chunk_users = unique_users.slice(start_idx, end_idx - start_idx)
            user_ids = chunk_users.select('user_id').to_series().to_list()
            
            # Bu user'ların tüm event'lerini al
            chunk_data = df.filter(pl.col('user_id').is_in(user_ids))
            
            # Future'ı submit et
            future = executor.submit(process_chunk_parallel, chunk_data, chunk_idx, total_chunks)
            futures.append(future)
        
        # Progress bar ile sonuçları bekle
        completed_count = 0
        with tqdm(total=total_chunks, desc="Chunk İşleniyor") as pbar:
            for future in as_completed(futures):
                try:
                    result = future.result()
                    completed_count += result
                    pbar.update(1)
                except Exception as e:
                    pbar.update(1)
    
    end_time = time.time()
    processing_time = end_time - start_time

def verify_event_name_features():
    """Event name features tablosunu doğrula"""
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    with engine.connect() as conn:
        # Toplam kayıt sayısı
        total_count = pd.read_sql("SELECT COUNT(*) as total FROM event_name_features", conn)
        print(f"📊 Toplam kayıt: {total_count['total'].iloc[0]:,}")
        
        # Örnek kayıtlar
        sample_data = pd.read_sql("SELECT * FROM event_name_features LIMIT 5", conn)
        print("\n📋 Örnek Kayıtlar:")
        print(sample_data)
        
        # Feature istatistikleri
        stats_query = """
        SELECT 
            AVG(first_15_days_total_revenue) as avg_revenue,
            AVG(first_15_days_total_events) as avg_events,
            SUM(has_subscribe_in_first_15_days) as total_subscribers,
            SUM(has_renewal_in_first_15_days) as total_renewals
        FROM event_name_features
        """
        stats = pd.read_sql(stats_query, conn)
        print("\n📈 Feature İstatistikleri:")
        print(stats)

def main():
    """Ana fonksiyon"""
    
    # 1. Tablo oluştur
    create_event_name_features_table()
    
    # 2. Feature'ları paralel işle
    process_event_name_features_parallel()
    
    # 3. Doğrula
    verify_event_name_features()

if __name__ == "__main__":
    main()
