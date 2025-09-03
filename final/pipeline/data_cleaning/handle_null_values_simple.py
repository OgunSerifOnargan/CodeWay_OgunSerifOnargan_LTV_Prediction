import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text

def handle_null_values_simple():
    """Sadece null değerleri günceller, ekstra sütun eklemez"""
    print("🔧 Basit Null Value Handling...")
    
    # Database connection
    try:
        # SQLAlchemy engine
        engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
        
        print("✅ Database bağlantısı başarılı")
        
        # Önce mevcut null durumunu kontrol et
        print(f"\n📋 MEVCUT NULL DURUMU:")
        
        with engine.connect() as conn:
            # Null sayılarını kontrol et
            null_check_query = """
            SELECT 
                'country' as column_name,
                COUNT(*) as null_count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_dataset), 4) as null_percentage
            FROM raw_dataset 
            WHERE country IS NULL
            
            UNION ALL
            
            SELECT 
                'revenue' as column_name,
                COUNT(*) as null_count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_dataset), 4) as null_percentage
            FROM raw_dataset 
            WHERE revenue IS NULL
            """
            
            null_results = pd.read_sql(null_check_query, conn)
            
            for _, row in null_results.iterrows():
                print(f"   {row['column_name']}: {row['null_count']:,} null ({row['null_percentage']:.2f}%)")
        
        # Null değerleri handle et
        print(f"\n🔧 NULL DEĞERLERİ GÜNCELLİYORUM...")
        
        with engine.connect() as conn:
            # Transaction başlat
            trans = conn.begin()
            
            try:
                # 1. Country null'larını UNK ile doldur
                print("   Country null'larını UNK ile dolduruyorum...")
                country_update = text("""
                                    UPDATE test_raw_dataset 
                SET country = 'UNK' 
                WHERE country IS NULL
                """)
                conn.execute(country_update)
                
                # 2. Revenue null'larını 0 ile doldur
                print("   Revenue null'larını 0 ile dolduruyorum...")
                revenue_update = text("""
                                    UPDATE test_raw_dataset 
                SET revenue = 0.0 
                WHERE revenue IS NULL
                """)
                conn.execute(revenue_update)
                
                # Transaction'ı commit et
                trans.commit()
                print("✅ Transaction başarıyla commit edildi")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Hata: {e}")
                raise
        
        # Sonuçları kontrol et
        print(f"\n✅ GÜNCELLENMİŞ VERİ KONTROLÜ:")
        
        with engine.connect() as conn:
            # Güncel null durumu
            final_null_check = """
            SELECT 
                'country' as column_name,
                COUNT(*) as null_count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_dataset), 4) as null_percentage
            FROM raw_dataset 
            WHERE country IS NULL
            
            UNION ALL
            
            SELECT 
                'revenue' as column_name,
                COUNT(*) as null_count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_dataset), 4) as null_percentage
            FROM raw_dataset 
            WHERE revenue IS NULL
            """
            
            final_null_results = pd.read_sql(final_null_check, conn)
            
            print(f"\n📋 GÜNCEL NULL DURUMU:")
            for _, row in final_null_results.iterrows():
                print(f"   {row['column_name']}: {row['null_count']:,} null ({row['null_percentage']:.2f}%)")
            
            # Country dağılımı
            country_dist = """
            SELECT 
                country,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_dataset), 2) as percentage
            FROM raw_dataset 
            GROUP BY country 
            ORDER BY count DESC 
            LIMIT 10
            """
            
            country_results = pd.read_sql(country_dist, conn)
            
            print(f"\n🌍 COUNTRY DAĞILIMI (İlk 10):")
            for _, row in country_results.iterrows():
                print(f"   {row['country']}: {row['count']:,} ({row['percentage']:.2f}%)")
            
            # Revenue dağılımı
            revenue_dist = """
            SELECT 
                revenue,
                COUNT(*) as count
            FROM raw_dataset 
            WHERE revenue > 0
            GROUP BY revenue
            ORDER BY revenue 
            LIMIT 5
            """
            
            revenue_results = pd.read_sql(revenue_dist, conn)
            
            print(f"\n💰 NON-ZERO REVENUE ÖRNEKLERİ:")
            for _, row in revenue_results.iterrows():
                print(f"   ${row['revenue']:.2f}: {row['count']:,} events")
            
            # Sütun listesi
            columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'raw_dataset' 
            ORDER BY ordinal_position
            """
            
            columns_results = pd.read_sql(columns_query, conn)
            
            print(f"\n📋 GÜNCEL SÜTUNLAR:")
            for _, row in columns_results.iterrows():
                print(f"   {row['column_name']} ({row['data_type']})")
        
        print(f"\n✅ NULL VALUE HANDLING TAMAMLANDI!")
        print(f"   - Country null'ları 'UNK' ile dolduruldu")
        print(f"   - Revenue null'ları $0.0 ile dolduruldu")
        print(f"   - Ekstra sütun eklenmedi")
        
    except Exception as e:
        print(f"❌ Database hatası: {e}")

if __name__ == "__main__":
    handle_null_values_simple()
