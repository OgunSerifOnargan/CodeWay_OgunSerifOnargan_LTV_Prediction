import polars as pl
import numpy as np

def analyze_null_values():
    """Null value analizi ve handle etme stratejileri"""
    print("🔍 Null Value Analizi...")
    
    # Parquet dosyasını oku
    df = pl.read_parquet('ltvprediction_case.parquet')
    
    print(f"📊 Toplam satır: {len(df):,}")
    print(f"📊 Toplam sütun: {len(df.columns)}")
    
    # Her sütun için null analizi
    print(f"\n📋 NULL VALUE ANALİZİ:")
    print("=" * 80)
    
    null_stats = []
    
    for col in df.columns:
        # Null sayısı
        null_count = df.filter(pl.col(col).is_null()).height
        null_percentage = (null_count / len(df)) * 100
        
        # Sütun tipi
        col_type = df.schema[col]
        
        # Unique değer sayısı (null hariç)
        unique_count = df.filter(pl.col(col).is_not_null()).select(col).n_unique()
        
        null_stats.append({
            'column': col,
            'null_count': null_count,
            'null_percentage': null_percentage,
            'data_type': col_type,
            'unique_values': unique_count
        })
        
        # Null durumuna göre emoji
        if null_count == 0:
            status = "✅"
        elif null_percentage < 1:
            status = "⚠️"
        elif null_percentage < 10:
            status = "🔶"
        else:
            status = "❌"
        
        print(f"{status} {col:<20} | {null_count:>8,} null ({null_percentage:>5.2f}%) | {col_type} | {unique_count:,} unique")
    
    # Null olan sütunların detaylı analizi
    print(f"\n🔍 NULL OLAN SÜTUNLARIN DETAYLI ANALİZİ:")
    print("=" * 80)
    
    for stat in null_stats:
        if stat['null_count'] > 0:
            col = stat['column']
            print(f"\n📊 SÜTUN: {col}")
            print(f"   Null sayısı: {stat['null_count']:,} ({stat['null_percentage']:.2f}%)")
            print(f"   Veri tipi: {stat['data_type']}")
            print(f"   Unique değer sayısı: {stat['unique_values']:,}")
            
            # Null olmayan değerlerin örnekleri
            non_null_sample = df.filter(pl.col(col).is_not_null()).select(col).head(5)
            print(f"   Örnek değerler: {non_null_sample[col].to_list()}")
            
            # Null olan satırların diğer sütunlardaki değerleri
            null_rows = df.filter(pl.col(col).is_null()).head(3)
            print(f"   Null olan satırların örnekleri:")
            for i, row in enumerate(null_rows.iter_rows()):
                print(f"     Satır {i+1}: {dict(zip(df.columns, row))}")
    
    # Null pattern analizi
    print(f"\n🔍 NULL PATTERN ANALİZİ:")
    print("=" * 50)
    
    # Birden fazla null olan satırlar
    null_columns = [stat['column'] for stat in null_stats if stat['null_count'] > 0]
    
    if len(null_columns) > 1:
        print(f"   Birden fazla null sütunu var: {null_columns}")
        
        # Aynı satırda birden fazla null olan durumlar
        for i, col1 in enumerate(null_columns):
            for col2 in null_columns[i+1:]:
                both_null = df.filter(
                    pl.col(col1).is_null() & pl.col(col2).is_null()
                ).height
                
                if both_null > 0:
                    print(f"   {col1} + {col2} aynı anda null: {both_null:,} satır")
    
    # Handle etme stratejileri
    print(f"\n💡 NULL VALUE HANDLE ETME STRATEJİLERİ:")
    print("=" * 60)
    
    for stat in null_stats:
        if stat['null_count'] > 0:
            col = stat['column']
            null_pct = stat['null_percentage']
            data_type = stat['data_type']
            
            print(f"\n📊 {col} ({null_pct:.2f}% null):")
            
            # Strateji önerileri
            if null_pct < 1:
                print(f"   🟢 Düşük null oranı - Basit imputation:")
                if data_type in [pl.Float64, pl.Int64]:
                    print(f"      - Mean/median ile doldur")
                    print(f"      - Mode ile doldur")
                else:
                    print(f"      - Mode ile doldur")
                    print(f"      - 'Unknown' kategorisi ekle")
            
            elif null_pct < 10:
                print(f"   🟡 Orta null oranı - Dikkatli imputation:")
                if data_type in [pl.Float64, pl.Int64]:
                    print(f"      - Mean/median ile doldur")
                    print(f"      - KNN imputation düşün")
                else:
                    print(f"      - Mode ile doldur")
                    print(f"      - 'Missing' kategorisi ekle")
                    print(f"      - Null indicator feature ekle")
            
            else:
                print(f"   🔴 Yüksek null oranı - Özel strateji:")
                print(f"      - Null indicator feature ekle")
                print(f"      - Kategorik ise 'Missing' kategorisi")
                print(f"      - Numeric ise 0 veya -1 ile doldur")
                print(f"      - Model'de null handling düşün")
    
    # Genel öneriler
    print(f"\n🎯 GENEL STRATEJİ ÖNERİLERİ:")
    print("=" * 50)
    
    print(f"   1. 📊 Null Indicator Features:")
    print(f"      - Her null sütunu için binary indicator ekle")
    print(f"      - Örnek: is_country_null, is_revenue_null")
    
    print(f"\n   2. 🔄 Imputation Stratejileri:")
    print(f"      - Numeric: Mean, median, mode")
    print(f"      - Categorical: Mode, 'Unknown' kategorisi")
    print(f"      - Time-based: Forward fill, backward fill")
    
    print(f"\n   3. 🎯 LTV Prediction İçin Özel Stratejiler:")
    print(f"      - Revenue null'ları: $0.0 ile doldur (ödeme yapmamış)")
    print(f"      - Country null'ları: 'Unknown' kategorisi ekle")
    print(f"      - Null indicator'ları feature olarak kullan")
    
    print(f"\n   4. 📈 Model Performance:")
    print(f"      - Null handling'den önce ve sonra model karşılaştır")
    print(f"      - Null indicator feature'larının etkisini test et")
    print(f"      - Domain knowledge ile imputation stratejisi belirle")

if __name__ == "__main__":
    analyze_null_values()
