import polars as pl
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

def load_and_prepare_data():
    """Veriyi yükle ve hazırla"""
    print("📂 Veri yükleniyor...")
    df = pl.read_parquet('ltvprediction_case.parquet')
    df_pandas = df.to_pandas()
    
    print("⏰ Event time'ları dönüştürülüyor...")
    df_pandas['event_datetime'] = pd.to_datetime(df_pandas['event_time'], unit='ms')
    
    # Time-based features ekle
    df_pandas['hour_of_day'] = df_pandas['event_datetime'].dt.hour
    df_pandas['day_of_week'] = df_pandas['event_datetime'].dt.dayofweek
    df_pandas['day_of_week_name'] = df_pandas['event_datetime'].dt.day_name()
    df_pandas['is_weekend'] = df_pandas['day_of_week'].isin([5, 6])
    
    print(f"📊 Toplam events: {len(df_pandas):,}")
    print(f"📊 Unique users: {df_pandas['user_id'].nunique():,}")
    
    return df_pandas

def analyze_event_timing_distribution(df):
    """Event timing dağılımını analiz et"""
    print("\n🕐 EVENT TIMING DAĞILIMI ANALİZİ...")
    
    # Hour of day distribution
    print("📊 Saat bazında event dağılımı:")
    hour_dist = df['hour_of_day'].value_counts().sort_index()
    for hour, count in hour_dist.items():
        percentage = (count / len(df)) * 100
        print(f"   {hour:02d}:00 - {count:,} event ({percentage:.1f}%)")
    
    # Day of week distribution
    print("\n📊 Haftanın günleri bazında event dağılımı:")
    day_dist = df['day_of_week_name'].value_counts()
    for day, count in day_dist.items():
        percentage = (count / len(df)) * 100
        print(f"   {day} - {count:,} event ({percentage:.1f}%)")
    
    # Weekend vs weekday
    weekend_ratio = df['is_weekend'].mean() * 100
    print(f"\n📊 Hafta sonu aktivite oranı: {weekend_ratio:.1f}%")
    
    return hour_dist, day_dist, weekend_ratio

def analyze_event_interval_patterns(df):
    """Event interval pattern'lerini analiz et"""
    print("\n⏱️ EVENT INTERVAL PATTERN ANALİZİ...")
    
    # Her user için event interval'larını hesapla
    intervals = []
    
    for user_id in tqdm(df['user_id'].unique(), desc="Interval hesaplanıyor"):
        user_events = df[df['user_id'] == user_id].sort_values('event_time')
        
        if len(user_events) > 1:
            for i in range(1, len(user_events)):
                interval = (user_events.iloc[i]['event_time'] - user_events.iloc[i-1]['event_time']) / 1000 / 60  # dakika
                intervals.append({
                    'user_id': user_id,
                    'interval_minutes': interval,
                    'event_type': user_events.iloc[i]['event_name']
                })
    
    intervals_df = pd.DataFrame(intervals)
    
    if len(intervals_df) > 0:
        print(f"📊 Toplam interval: {len(intervals_df):,}")
        print(f"📊 Ortalama interval: {intervals_df['interval_minutes'].mean():.1f} dakika")
        print(f"📊 Medyan interval: {intervals_df['interval_minutes'].median():.1f} dakika")
        print(f"📊 Maksimum interval: {intervals_df['interval_minutes'].max():.1f} dakika")
        
        # Interval kategorileri
        intervals_df['interval_category'] = pd.cut(
            intervals_df['interval_minutes'], 
            bins=[0, 1, 5, 15, 60, 1440, float('inf')],
            labels=['<1min', '1-5min', '5-15min', '15-60min', '1-24h', '>24h']
        )
        
        interval_categories = intervals_df['interval_category'].value_counts()
        print("\n📊 Interval kategorileri:")
        for category, count in interval_categories.items():
            percentage = (count / len(intervals_df)) * 100
            print(f"   {category} - {count:,} ({percentage:.1f}%)")
    
    return intervals_df

def analyze_event_sequence_patterns(df):
    """Event sequence pattern'lerini analiz et"""
    print("\n🔄 EVENT SEQUENCE PATTERN ANALİZİ...")
    
    # Her user için event sequence'ini çıkar
    sequences = []
    
    for user_id in tqdm(df['user_id'].unique(), desc="Sequence'ler çıkarılıyor"):
        user_events = df[df['user_id'] == user_id].sort_values('event_time')
        sequence = user_events['event_name'].tolist()
        sequences.append({
            'user_id': user_id,
            'sequence': sequence,
            'sequence_length': len(sequence)
        })
    
    sequences_df = pd.DataFrame(sequences)
    
    # En yaygın sequence'leri bul
    print("📊 En yaygın event sequence'leri:")
    sequence_counts = Counter()
    
    for sequence in sequences_df['sequence']:
        if len(sequence) >= 2:
            # 2'li kombinasyonlar
            for i in range(len(sequence) - 1):
                pair = f"{sequence[i]} -> {sequence[i+1]}"
                sequence_counts[pair] += 1
            
            # 3'lü kombinasyonlar
            if len(sequence) >= 3:
                for i in range(len(sequence) - 2):
                    triplet = f"{sequence[i]} -> {sequence[i+1]} -> {sequence[i+2]}"
                    sequence_counts[triplet] += 1
    
    # Top 10 sequence'leri göster
    top_sequences = sequence_counts.most_common(10)
    for i, (sequence, count) in enumerate(top_sequences, 1):
        percentage = (count / len(sequences_df)) * 100
        print(f"   {i}. {sequence} - {count:,} user ({percentage:.1f}%)")
    
    return sequences_df, sequence_counts

def analyze_time_based_user_segments(df):
    """Time-based user segmentasyonu"""
    print("\n👥 TIME-BASED USER SEGMENTASYONU...")
    
    # Her user için peak activity hour'ını bul
    user_peak_hours = []
    
    for user_id in tqdm(df['user_id'].unique(), desc="Peak hour'lar hesaplanıyor"):
        user_events = df[df['user_id'] == user_id]
        if len(user_events) > 0:
            peak_hour = user_events['hour_of_day'].mode().iloc[0]
            total_events = len(user_events)
            weekend_ratio = user_events['is_weekend'].mean()
            
            user_peak_hours.append({
                'user_id': user_id,
                'peak_hour': peak_hour,
                'total_events': total_events,
                'weekend_ratio': weekend_ratio
            })
    
    user_peak_df = pd.DataFrame(user_peak_hours)
    
    # Time segment'leri oluştur
    def get_time_segment(hour):
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        elif 18 <= hour < 24:
            return 'evening'
        else:
            return 'night'
    
    user_peak_df['time_segment'] = user_peak_df['peak_hour'].apply(get_time_segment)
    
    # Segment dağılımını analiz et
    segment_dist = user_peak_df['time_segment'].value_counts()
    print("📊 Time segment dağılımı:")
    for segment, count in segment_dist.items():
        percentage = (count / len(user_peak_df)) * 100
        print(f"   {segment} - {count:,} user ({percentage:.1f}%)")
    
    # Weekend vs weekday user'ları
    weekend_users = user_peak_df[user_peak_df['weekend_ratio'] > 0.5]
    weekday_users = user_peak_df[user_peak_df['weekend_ratio'] <= 0.5]
    
    print(f"\n📊 Weekend-focused user'lar: {len(weekend_users):,} ({len(weekend_users)/len(user_peak_df)*100:.1f}%)")
    print(f"📊 Weekday-focused user'lar: {len(weekend_users):,} ({len(weekday_users)/len(user_peak_df)*100:.1f}%)")
    
    return user_peak_df

def analyze_consistency_patterns(df):
    """User consistency pattern'lerini analiz et"""
    print("\n🎯 USER CONSISTENCY PATTERN ANALİZİ...")
    
    consistency_scores = []
    
    for user_id in tqdm(df['user_id'].unique(), desc="Consistency hesaplanıyor"):
        user_events = df[df['user_id'] == user_id].sort_values('event_time')
        
        if len(user_events) > 1:
            # Hour consistency
            hour_std = user_events['hour_of_day'].std()
            hour_consistency = 1 / (1 + hour_std) if hour_std > 0 else 1
            
            # Day consistency
            day_std = user_events['day_of_week'].std()
            day_consistency = 1 / (1 + day_std) if day_std > 0 else 1
            
            # Event type consistency
            event_diversity = user_events['event_name'].nunique()
            event_consistency = 1 / event_diversity if event_diversity > 0 else 1
            
            # Overall consistency score
            overall_consistency = (hour_consistency + day_consistency + event_consistency) / 3
            
            consistency_scores.append({
                'user_id': user_id,
                'hour_consistency': hour_consistency,
                'day_consistency': day_consistency,
                'event_consistency': event_consistency,
                'overall_consistency': overall_consistency,
                'total_events': len(user_events)
            })
    
    consistency_df = pd.DataFrame(consistency_scores)
    
    if len(consistency_df) > 0:
        print(f"📊 Ortalama overall consistency: {consistency_df['overall_consistency'].mean():.3f}")
        print(f"📊 Ortalama hour consistency: {consistency_df['hour_consistency'].mean():.3f}")
        print(f"📊 Ortalama day consistency: {consistency_df['day_consistency'].mean():.3f}")
        print(f"📊 Ortalama event consistency: {consistency_df['event_consistency'].mean():.3f}")
        
        # Consistency kategorileri
        consistency_df['consistency_category'] = pd.cut(
            consistency_df['overall_consistency'],
            bins=[0, 0.3, 0.6, 1.0],
            labels=['low_consistency', 'medium_consistency', 'high_consistency']
        )
        
        consistency_categories = consistency_df['consistency_category'].value_counts()
        print("\n📊 Consistency kategorileri:")
        for category, count in consistency_categories.items():
            percentage = (count / len(consistency_df)) * 100
            print(f"   {category} - {count:,} user ({percentage:.1f}%)")
    
    return consistency_df

def create_time_pattern_visualizations(df, hour_dist, day_dist, user_peak_df, consistency_df):
    """Time pattern görselleştirmelerini oluştur"""
    print("\n📊 Time pattern görselleştirmeleri oluşturuluyor...")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Time Pattern Analysis', fontsize=16, fontweight='bold')
    
    # 1. Hour of day distribution
    ax1 = axes[0, 0]
    hour_dist.plot(kind='bar', ax=ax1, color='skyblue', alpha=0.7)
    ax1.set_title('Event Distribution by Hour of Day')
    ax1.set_xlabel('Hour of Day')
    ax1.set_ylabel('Event Count')
    ax1.grid(True, alpha=0.3)
    
    # 2. Day of week distribution
    ax2 = axes[0, 1]
    day_dist.plot(kind='bar', ax=ax2, color='lightgreen', alpha=0.7)
    ax2.set_title('Event Distribution by Day of Week')
    ax2.set_xlabel('Day of Week')
    ax2.set_ylabel('Event Count')
    ax2.grid(True, alpha=0.3)
    
    # 3. Time segment distribution
    ax3 = axes[0, 2]
    segment_dist = user_peak_df['time_segment'].value_counts()
    segment_dist.plot(kind='pie', ax=ax3, autopct='%1.1f%%', colors=['lightcoral', 'lightblue', 'lightgreen', 'gold'])
    ax3.set_title('User Distribution by Time Segment')
    
    # 4. Consistency distribution
    ax4 = axes[1, 0]
    consistency_df['overall_consistency'].hist(bins=30, ax=ax4, color='orange', alpha=0.7, edgecolor='black')
    ax4.set_title('Distribution of User Consistency Scores')
    ax4.set_xlabel('Consistency Score')
    ax4.set_ylabel('User Count')
    ax4.grid(True, alpha=0.3)
    
    # 5. Peak hour distribution
    ax5 = axes[1, 1]
    user_peak_df['peak_hour'].hist(bins=24, ax=ax5, color='purple', alpha=0.7, edgecolor='black')
    ax5.set_title('Distribution of User Peak Hours')
    ax5.set_xlabel('Peak Hour')
    ax5.set_ylabel('User Count')
    ax5.grid(True, alpha=0.3)
    
    # 6. Weekend ratio distribution
    ax6 = axes[1, 2]
    user_peak_df['weekend_ratio'].hist(bins=20, ax=ax6, color='coral', alpha=0.7, edgecolor='black')
    ax6.set_title('Distribution of Weekend Activity Ratio')
    ax6.set_xlabel('Weekend Activity Ratio')
    ax6.set_ylabel('User Count')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('time_pattern_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("✅ Görselleştirmeler kaydedildi: 'time_pattern_analysis.png'")

def analyze_lstm_potential(df, sequences_df, consistency_df):
    """LSTM potansiyelini analiz et"""
    print("\n🧠 LSTM POTANSİYEL ANALİZİ...")
    
    # Time pattern strength hesapla
    pattern_strength_indicators = {}
    
    # 1. Consistency strength
    avg_consistency = consistency_df['overall_consistency'].mean()
    pattern_strength_indicators['consistency_strength'] = avg_consistency
    
    # 2. Sequence pattern strength
    unique_sequences = sequences_df['sequence_length'].nunique()
    avg_sequence_length = sequences_df['sequence_length'].mean()
    pattern_strength_indicators['sequence_complexity'] = unique_sequences / avg_sequence_length
    
    # 3. Time regularity
    hour_consistency = consistency_df['hour_consistency'].mean()
    day_consistency = consistency_df['day_consistency'].mean()
    pattern_strength_indicators['time_regularity'] = (hour_consistency + day_consistency) / 2
    
    # 4. Event predictability
    event_consistency = consistency_df['event_consistency'].mean()
    pattern_strength_indicators['event_predictability'] = event_consistency
    
    # Overall pattern strength
    overall_pattern_strength = np.mean(list(pattern_strength_indicators.values()))
    
    print("📊 Pattern Strength Indicators:")
    for indicator, value in pattern_strength_indicators.items():
        print(f"   {indicator}: {value:.3f}")
    
    print(f"\n📊 Overall Pattern Strength: {overall_pattern_strength:.3f}")
    
    # LSTM recommendation
    if overall_pattern_strength > 0.6:
        recommendation = "STRONG - LSTM highly recommended"
    elif overall_pattern_strength > 0.4:
        recommendation = "MODERATE - LSTM worth trying"
    else:
        recommendation = "WEAK - Traditional ML recommended"
    
    print(f"🎯 LSTM Recommendation: {recommendation}")
    
    return pattern_strength_indicators, overall_pattern_strength, recommendation

def main():
    """Ana fonksiyon"""
    print("🕐 TIME PATTERN ANALİZİ")
    print("=" * 80)
    
    # Veriyi yükle
    df = load_and_prepare_data()
    
    # Event timing distribution
    hour_dist, day_dist, weekend_ratio = analyze_event_timing_distribution(df)
    
    # Event interval patterns
    intervals_df = analyze_event_interval_patterns(df)
    
    # Event sequence patterns
    sequences_df, sequence_counts = analyze_event_sequence_patterns(df)
    
    # Time-based user segments
    user_peak_df = analyze_time_based_user_segments(df)
    
    # Consistency patterns
    consistency_df = analyze_consistency_patterns(df)
    
    # Görselleştirmeler
    create_time_pattern_visualizations(df, hour_dist, day_dist, user_peak_df, consistency_df)
    
    # LSTM potential analysis
    pattern_indicators, pattern_strength, recommendation = analyze_lstm_potential(df, sequences_df, consistency_df)
    
    # Sonuçları kaydet
    print("\n💾 Sonuçlar kaydediliyor...")
    
    # Summary statistics
    summary_stats = {
        'total_events': len(df),
        'unique_users': df['user_id'].nunique(),
        'weekend_activity_ratio': weekend_ratio,
        'avg_consistency_score': consistency_df['overall_consistency'].mean() if len(consistency_df) > 0 else 0,
        'pattern_strength': pattern_strength,
        'lstm_recommendation': recommendation
    }
    
    # CSV dosyaları
    user_peak_df.to_csv('time_pattern_user_segments.csv', index=False)
    consistency_df.to_csv('time_pattern_consistency_scores.csv', index=False)
    sequences_df.to_csv('time_pattern_sequences.csv', index=False)
    
    if len(intervals_df) > 0:
        intervals_df.to_csv('time_pattern_intervals.csv', index=False)
    
    print(f"\n💾 Sonuçlar kaydedildi:")
    print(f"   - 'time_pattern_analysis.png'")
    print(f"   - 'time_pattern_user_segments.csv'")
    print(f"   - 'time_pattern_consistency_scores.csv'")
    print(f"   - 'time_pattern_sequences.csv'")
    if len(intervals_df) > 0:
        print(f"   - 'time_pattern_intervals.csv'")
    
    print(f"\n🎯 LSTM RECOMMENDATION: {recommendation}")
    print(f"📊 Pattern Strength: {pattern_strength:.3f}")
    
    print(f"\n🎉 TIME PATTERN ANALİZİ TAMAMLANDI!")

if __name__ == "__main__":
    main()
