import polars as pl
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

def create_country_features_table():
    """Country features tablosunu oluştur"""
    print("🗄️ Country Features Tablosu Oluşturuluyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Önce tabloyu sil
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS country_features"))
        conn.commit()
    
    create_table_sql = """
    CREATE TABLE test_country_features (
        country VARCHAR(50) PRIMARY KEY,
        
        -- User Counts
        total_users INTEGER DEFAULT 0,
        paying_users INTEGER DEFAULT 0,
        
        -- Revenue Metrics (15 days)
        avg_15_days_revenue DECIMAL(10,4) DEFAULT 0.0,
        total_15_days_revenue DECIMAL(15,4) DEFAULT 0.0,
        median_15_days_revenue DECIMAL(10,4) DEFAULT 0.0,
        revenue_per_user DECIMAL(10,4) DEFAULT 0.0,
        
        -- Conversion Metrics
        conversion_rate DECIMAL(5,4) DEFAULT 0.0,
        paying_user_ratio DECIMAL(5,4) DEFAULT 0.0,
        
        -- Engagement Metrics (15 days)
        avg_15_days_events DECIMAL(8,2) DEFAULT 0.0,
        avg_15_days_active_days DECIMAL(5,2) DEFAULT 0.0,
        avg_15_days_event_diversity DECIMAL(5,2) DEFAULT 0.0,
        
        -- Binary Metrics (15 days)
        avg_has_subscribe DECIMAL(5,4) DEFAULT 0.0,
        avg_has_renewal DECIMAL(5,4) DEFAULT 0.0,
        avg_has_trial DECIMAL(5,4) DEFAULT 0.0,
        
        -- Categories
        revenue_category VARCHAR(20) DEFAULT 'Unknown',
        conversion_category VARCHAR(20) DEFAULT 'Unknown',
        
        -- Scores (Normalized)
        revenue_score DECIMAL(8,6) DEFAULT 0.0,
        conversion_score DECIMAL(8,6) DEFAULT 0.0,
        composite_score DECIMAL(8,6) DEFAULT 0.0
    );
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✅ Country Features tablosu oluşturuldu!")

def get_country_data_from_15days():
    """15 günlük verilerden ülke bazında analiz yap"""
    print("📊 15 Günlük Verilerden Ülke Analizi...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # Event name features ve raw dataset'i join et
    query = """
    SELECT 
        rd.country,
        COUNT(*) as total_users,
        COUNT(CASE WHEN enf.has_revenue_in_first_15_days = 1 THEN 1 END) as paying_users,
        
        -- Revenue Metrics
        AVG(enf.first_15_days_total_revenue) as avg_15_days_revenue,
        SUM(enf.first_15_days_total_revenue) as total_15_days_revenue,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY enf.first_15_days_total_revenue) as median_15_days_revenue,
        SUM(enf.first_15_days_total_revenue) / COUNT(*) as revenue_per_user,
        
        -- Conversion Rate
        ROUND(COUNT(CASE WHEN enf.has_revenue_in_first_15_days = 1 THEN 1 END) * 100.0 / COUNT(*), 4) as conversion_rate,
        ROUND(COUNT(CASE WHEN enf.has_revenue_in_first_15_days = 1 THEN 1 END) * 1.0 / COUNT(*), 4) as paying_user_ratio,
        
        -- Engagement Metrics
        AVG(enf.first_15_days_total_events) as avg_15_days_events,
        AVG(enf.first_15_days_active_days) as avg_15_days_active_days,
        AVG(enf.first_15_days_event_diversity) as avg_15_days_event_diversity,
        
        -- Binary Metrics
        AVG(enf.has_subscribe_in_first_15_days) as avg_has_subscribe,
        AVG(enf.has_renewal_in_first_15_days) as avg_has_renewal,
        AVG(enf.has_trial_in_first_15_days) as avg_has_trial
        
    FROM event_name_features enf
    JOIN raw_dataset rd ON enf.user_id = rd.user_id
    WHERE rd.country IS NOT NULL 
        AND rd.country != 'UNK'
    GROUP BY rd.country
    HAVING COUNT(*) >= 50  -- Minimum 50 kullanıcı
    ORDER BY avg_15_days_revenue DESC
    """
    
    try:
        df = pd.read_sql(query, engine)
        print(f"📊 {len(df)} ülke analiz edildi")
        return df
    except Exception as e:
        print(f"❌ Veri çekme hatası: {e}")
        return None

def calculate_normalized_scores(df):
    """Normalize edilmiş score'ları hesapla"""
    print("🧮 Normalize edilmiş score'lar hesaplanıyor...")
    
    # Revenue Score (avg_15_days_revenue based)
    min_revenue = df['avg_15_days_revenue'].min()
    max_revenue = df['avg_15_days_revenue'].max()
    df['revenue_score'] = (df['avg_15_days_revenue'] - min_revenue) / (max_revenue - min_revenue)
    
    # Conversion Score (conversion_rate based)
    min_conversion = df['conversion_rate'].min()
    max_conversion = df['conversion_rate'].max()
    df['conversion_score'] = (df['conversion_rate'] - min_conversion) / (max_conversion - min_conversion)
    
    # Composite Score (weighted average)
    df['composite_score'] = (df['revenue_score'] * 0.6) + (df['conversion_score'] * 0.4)
    
    print(f"📊 Score Ranges:")
    print(f"   Revenue Score: {df['revenue_score'].min():.6f} - {df['revenue_score'].max():.6f}")
    print(f"   Conversion Score: {df['conversion_score'].min():.6f} - {df['conversion_score'].max():.6f}")
    print(f"   Composite Score: {df['composite_score'].min():.6f} - {df['composite_score'].max():.6f}")
    
    return df

def categorize_by_quarters(df, column, category_name):
    """Quarter'lara göre kategorize et"""
    
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    
    print(f"\n📊 {category_name} QUARTER DEĞERLERİ:")
    print(f"Q1 (25. percentile): {q1:.6f}")
    print(f"Q3 (75. percentile): {q3:.6f}")
    
    def categorize_score(score):
        if score <= q1:
            return f'Low {category_name}'
        elif score <= q3:
            return f'Mid {category_name}'
        else:
            return f'High {category_name}'
    
    category_column = f'{category_name.lower()}_category'
    df[category_column] = df[column].apply(categorize_score)
    
    return df, q1, q3

def analyze_categories(df):
    """Kategori analizini yap"""
    print(f"\n🎯 KATEGORİ DAĞILIMI:")
    print("=" * 80)
    
    # Revenue Categories
    revenue_cats = df.groupby('revenue_category').agg({
        'country': 'count',
        'total_users': 'sum',
        'avg_15_days_revenue': ['mean', 'min', 'max'],
        'revenue_score': ['mean', 'min', 'max']
    }).round(4)
    
    print("📊 REVENUE CATEGORIES:")
    print(revenue_cats)
    
    # Conversion Categories
    conversion_cats = df.groupby('conversion_category').agg({
        'country': 'count',
        'total_users': 'sum',
        'conversion_rate': ['mean', 'min', 'max'],
        'conversion_score': ['mean', 'min', 'max']
    }).round(4)
    
    print("\n📊 CONVERSION CATEGORIES:")
    print(conversion_cats)
    
    # Cross Tabulation
    cross_tab = pd.crosstab(df['revenue_category'], df['conversion_category'], margins=True)
    print("\n🔄 REVENUE vs CONVERSION CROSS TABULATION:")
    print(cross_tab)

def show_top_countries(df):
    """En iyi ülkeleri göster"""
    print(f"\n🏆 EN İYİ 10 ÜLKE (Composite Score):")
    print("=" * 80)
    
    top_countries = df.nlargest(10, 'composite_score')[['country', 'total_users', 'avg_15_days_revenue', 
                                                       'conversion_rate', 'revenue_category', 
                                                       'conversion_category', 'composite_score']]
    
    for _, row in top_countries.iterrows():
        print(f"   {row['country']:<20} | Users: {row['total_users']:>6,} | "
              f"Revenue: ${row['avg_15_days_revenue']:>6.2f} | "
              f"Conv: {row['conversion_rate']:>5.2f}% | "
              f"Score: {row['composite_score']:>6.4f} | "
              f"{row['revenue_category']} | {row['conversion_category']}")

def create_visualizations(df):
    """Görselleştirmeler oluştur"""
    print("🎨 Görselleştirmeler oluşturuluyor...")
    
    # 1. Revenue vs Conversion Scatter
    fig = px.scatter(df, x='revenue_score', y='conversion_score', 
                     color='revenue_category', size='total_users',
                     hover_data=['country', 'avg_15_days_revenue', 'conversion_rate'],
                     title='Revenue Score vs Conversion Score by Country',
                     labels={'revenue_score': 'Revenue Score', 'conversion_score': 'Conversion Score'})
    fig.write_html('feature_countries/revenue_vs_conversion_scatter.html')
    
    # 2. Composite Score Distribution
    fig = px.histogram(df, x='composite_score', color='revenue_category',
                       title='Composite Score Distribution by Revenue Category',
                       nbins=30)
    fig.write_html('feature_countries/composite_score_distribution.html')
    
    # 3. Top Countries Bar Chart
    top_20 = df.nlargest(20, 'composite_score')
    fig = px.bar(top_20, x='country', y='composite_score', 
                 color='revenue_category',
                 title='Top 20 Countries by Composite Score')
    fig.update_xaxes(tickangle=45)
    fig.write_html('feature_countries/top_countries_composite_score.html')
    
    print("✅ Görselleştirmeler kaydedildi!")

def save_to_database(df):
    """Verileri database'e kaydet"""
    print("💾 Veriler database'e kaydediliyor...")
    
    engine = create_engine('postgresql://ogunserifonargan@localhost:5432/lvp_database')
    
    # DataFrame'i database'e kaydet
    with engine.connect() as conn:
        df.to_sql('test_country_features', conn, if_exists='replace', index=False)
        conn.commit()
    
    print(f"✅ {len(df)} ülke verisi country_features tablosuna kaydedildi!")

def create_user_level_update_script():
    """User level feature'ları güncellemek için SQL script oluştur"""
    print("📝 User level update script oluşturuluyor...")
    
    script_content = """
-- User level country features güncelleme scripti
-- Bu script ltv_features tablosuna country-based feature'ları ekler

-- 1. Country features sütunlarını ekle
ALTER TABLE ltv_features ADD COLUMN IF NOT EXISTS country_avg_15_days_revenue DECIMAL(10,4);
ALTER TABLE ltv_features ADD COLUMN IF NOT EXISTS country_conversion_rate DECIMAL(5,4);
ALTER TABLE ltv_features ADD COLUMN IF NOT EXISTS country_revenue_category_15days VARCHAR(20);
ALTER TABLE ltv_features ADD COLUMN IF NOT EXISTS country_conversion_category_15days VARCHAR(20);
ALTER TABLE ltv_features ADD COLUMN IF NOT EXISTS country_composite_score DECIMAL(8,6);

-- 2. Country features'ları güncelle
UPDATE ltv_features 
SET 
    country_avg_15_days_revenue = cf.avg_15_days_revenue,
    country_conversion_rate = cf.conversion_rate,
    country_revenue_category_15days = cf.revenue_category,
    country_conversion_category_15days = cf.conversion_category,
    country_composite_score = cf.composite_score
FROM country_features cf
WHERE ltv_features.country = cf.country;

-- 3. Kontrol sorgusu
SELECT 
    country_revenue_category_15days,
    country_conversion_category_15days,
    COUNT(*) as user_count
FROM ltv_features 
WHERE country_revenue_category_15days IS NOT NULL
GROUP BY country_revenue_category_15days, country_conversion_category_15days
ORDER BY user_count DESC;
"""
    
    with open('feature_countries/update_user_level_country_features.sql', 'w') as f:
        f.write(script_content)
    
    print("✅ SQL script oluşturuldu: update_user_level_country_features.sql")

def main():
    """Ana fonksiyon"""
    print("🌍 15 GÜNLÜK REVENUE BAZINDA COUNTRY FEATURES OLUŞTURMA")
    print("=" * 80)
    
    # 1. Tablo oluştur
    create_country_features_table()
    
    # 2. 15 günlük verilerden ülke analizi
    df = get_country_data_from_15days()
    
    if df is None:
        print("❌ Veri çekilemedi!")
        return
    
    # 3. Normalize edilmiş score'ları hesapla
    df = calculate_normalized_scores(df)
    
    # 4. Revenue kategorizasyonu
    df, rev_q1, rev_q3 = categorize_by_quarters(df, 'revenue_score', 'Revenue')
    
    # 5. Conversion kategorizasyonu
    df, conv_q1, conv_q3 = categorize_by_quarters(df, 'conversion_score', 'Conversion')
    
    # 6. Kategori analizi
    analyze_categories(df)
    
    # 7. En iyi ülkeleri göster
    show_top_countries(df)
    
    # 8. Görselleştirmeler
    create_visualizations(df)
    
    # 9. Database'e kaydet
    save_to_database(df)
    
    # 10. User level update script oluştur
    create_user_level_update_script()
    
    # 11. CSV'ye kaydet
    df.to_csv('feature_countries/country_features_15days.csv', index=False)
    
    print(f"\n🎉 COUNTRY FEATURES BAŞARIYLA OLUŞTURULDU!")
    print(f"📊 {len(df)} ülke analiz edildi")
    print(f"🎯 15 günlük revenue bazında kategorizasyon")
    print(f"💾 country_features tablosu oluşturuldu")
    print(f"📝 User level update script hazırlandı")

if __name__ == "__main__":
    main()
