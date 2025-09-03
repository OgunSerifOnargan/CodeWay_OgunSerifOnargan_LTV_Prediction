import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text
import warnings
from tqdm import tqdm
import time
warnings.filterwarnings('ignore')

def load_parquet_to_postgres_chunked():
    """Parquet dosyasını PostgreSQL'e vectorized ve chunked olarak yükler"""
    print("📊 Parquet dosyası vectorized olarak yükleniyor...")
    
    # Database connection
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    try:
        start_time = time.time()
        
        # Parquet dosyasını oku (vectorized)
        print("📖 Parquet dosyası okunuyor...")
        df = pd.read_parquet('/Users/ogunserifonargan/Work/LVP_codeway/ltvprediction_case.parquet')
        
        print(f"✅ Parquet dosyası okundu: {len(df):,} satır, {len(df.columns)} kolon")
        print(f"📊 Kolonlar: {list(df.columns)}")
        
        # Veri tiplerini kontrol et
        print(f"\n📋 Veri tipleri:")
        for col, dtype in df.dtypes.items():
            print(f"   {col}: {dtype}")
        
        # İlk birkaç satırı göster
        print(f"\n📄 İlk 5 satır:")
        print(df.head())
        
        # Null değerleri kontrol et (vectorized)
        print(f"\n🔍 Null değerler:")
        null_counts = df.isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                print(f"   {col}: {count:,} null ({count/len(df)*100:.2f}%)")
        
        # Memory usage
        memory_usage = df.memory_usage(deep=True).sum() / 1024**2
        print(f"\n💾 Memory usage: {memory_usage:.2f} MB")
        
        print(f"\n💾 PostgreSQL'e chunked olarak yükleniyor...")
        
        # Chunked loading için optimal chunk size hesapla
        total_rows = len(df)
        optimal_chunk_size = min(50000, max(10000, total_rows // 10))  # 10-50k arası
        
        print(f"📦 Chunk size: {optimal_chunk_size:,}")
        print(f"📦 Total chunks: {(total_rows + optimal_chunk_size - 1) // optimal_chunk_size}")
        
        # Chunked loading (vectorized)
        chunks = [df[i:i + optimal_chunk_size] for i in range(0, total_rows, optimal_chunk_size)]
        
        # Drop table if exists
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS test_raw_dataset"))
            conn.commit()
        
        # Load chunks with progress bar
        for i, chunk in enumerate(tqdm(chunks, desc="Loading chunks")):
            if_exists = 'replace' if i == 0 else 'append'
            
            # Vectorized operations on chunk
            chunk_processed = chunk.copy()
            
            # Optimize data types (vectorized)
            for col in chunk_processed.select_dtypes(include=['object']).columns:
                if chunk_processed[col].nunique() < chunk_processed[col].count() * 0.5:  # Low cardinality
                    chunk_processed[col] = chunk_processed[col].astype('category')
            
            # Save chunk (vectorized)
            chunk_processed.to_sql(
                'test_raw_dataset', 
                engine, 
                if_exists=if_exists, 
                index=False,
                method='multi',
                chunksize=10000
            )
            
            # Progress update
            if (i + 1) % 5 == 0:
                print(f"   ✅ {i + 1}/{len(chunks)} chunks loaded")
        
        elapsed_time = time.time() - start_time
        
        print(f"✅ test_raw_dataset tablosu oluşturuldu!")
        print(f"📊 {len(df):,} satır yüklendi")
        print(f"🎯 {len(df.columns)} kolon eklendi")
        print(f"⏱️  Toplam süre: {elapsed_time:.2f} saniye")
        print(f"🚀 Hız: {len(df)/elapsed_time:.0f} satır/saniye")
        
        # Tablo bilgilerini kontrol et
        print(f"\n📋 Tablo bilgileri:")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM test_raw_dataset")).fetchone()
            print(f"   Satır sayısı: {result[0]:,}")
            
            # Unique user sayısı
            result = conn.execute(text("SELECT COUNT(DISTINCT user_id) FROM test_raw_dataset")).fetchone()
            print(f"   Unique user sayısı: {result[0]:,}")
            
            # Target distribution (vectorized)
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_users,
                    AVG(first_year_revenue) as avg_ltv,
                    MIN(first_year_revenue) as min_ltv,
                    MAX(first_year_revenue) as max_ltv,
                    STDDEV(first_year_revenue) as std_ltv
                FROM test_raw_dataset 
                WHERE first_year_revenue IS NOT NULL
            """)).fetchone()
            
            print(f"   Target (first_year_revenue) istatistikleri:")
            print(f"     Total users: {result[0]:,}")
            print(f"     Avg LTV: ${result[1]:.2f}")
            print(f"     Min LTV: ${result[2]:.2f}")
            print(f"     Max LTV: ${result[3]:.2f}")
            print(f"     Std LTV: ${result[4]:.2f}")
            
            # Memory usage in database
            result = conn.execute(text("""
                SELECT pg_size_pretty(pg_total_relation_size('test_raw_dataset')) as table_size
            """)).fetchone()
            print(f"   Tablo boyutu: {result[0]}")
            
            # Indexes oluştur (performance için)
            print(f"\n🔍 Indexes oluşturuluyor...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_test_raw_user_id ON test_raw_dataset(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_test_raw_event_date ON test_raw_dataset(event_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_test_raw_country ON test_raw_dataset(country)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_test_raw_operating_system ON test_raw_dataset(operating_system)"))
            conn.commit()
            print(f"   ✅ Indexes oluşturuldu")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        raise

if __name__ == "__main__":
    load_parquet_to_postgres_chunked()
