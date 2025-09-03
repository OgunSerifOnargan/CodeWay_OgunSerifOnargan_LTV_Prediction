import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text

def remove_extra_columns():
    """Ekstra eklenen null indicator sütunlarını siler"""
    print("🗑️ Ekstra Sütunları Silme...")
    
    # Database connection
    try:
        # SQLAlchemy engine
        engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
        
        print("✅ Database bağlantısı başarılı")
        
        # Mevcut sütunları kontrol et
        print(f"\n📋 MEVCUT SÜTUNLAR:")
        
        with engine.connect() as conn:
            columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'raw_dataset' 
            ORDER BY ordinal_position
            """
            
            columns_results = pd.read_sql(columns_query, conn)
            
            for _, row in columns_results.iterrows():
                print(f"   {row['column_name']} ({row['data_type']})")
        
        # Ekstra sütunları sil
        print(f"\n🗑️ EKSTRA SÜTUNLARI SİLİYORUM...")
        
        with engine.connect() as conn:
            # Transaction başlat
            trans = conn.begin()
            
            try:
                # is_country_null sütununu sil
                print("   is_country_null sütununu siliyorum...")
                drop_country_null = text("""
                    ALTER TABLE raw_dataset 
                    DROP COLUMN IF EXISTS is_country_null
                """)
                conn.execute(drop_country_null)
                
                # is_revenue_null sütununu sil
                print("   is_revenue_null sütununu siliyorum...")
                drop_revenue_null = text("""
                    ALTER TABLE raw_dataset 
                    DROP COLUMN IF EXISTS is_revenue_null
                """)
                conn.execute(drop_revenue_null)
                
                # Transaction'ı commit et
                trans.commit()
                print("✅ Transaction başarıyla commit edildi")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Hata: {e}")
                raise
        
        # Sonuçları kontrol et
        print(f"\n✅ GÜNCEL SÜTUNLAR:")
        
        with engine.connect() as conn:
            final_columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'raw_dataset' 
            ORDER BY ordinal_position
            """
            
            final_columns_results = pd.read_sql(final_columns_query, conn)
            
            for _, row in final_columns_results.iterrows():
                print(f"   {row['column_name']} ({row['data_type']})")
        
        print(f"\n✅ EKSTRA SÜTUNLAR SİLİNDİ!")
        print(f"   - is_country_null sütunu silindi")
        print(f"   - is_revenue_null sütunu silindi")
        print(f"   - Sadece orijinal 9 sütun kaldı")
        
    except Exception as e:
        print(f"❌ Database hatası: {e}")

if __name__ == "__main__":
    remove_extra_columns()
