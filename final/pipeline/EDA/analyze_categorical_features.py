import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency, f_oneway
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def analyze_categorical_features():
    """Analyze all categorical features across user-level tables"""
    
    print("🏷️ ANALYZING CATEGORICAL FEATURES FOR LTV PREDICTION...")
    engine = create_engine(DB_URL)
    
    # Load all feature tables
    feature_tables = [
        'post_subscription_features', 
        'pre_subscription_features',
        'revenue_features',
        'rfm_features',
        'training_table'
    ]
    
    # Get target data
    target_query = """
    SELECT 
        user_id,
        first_year_revenue,
        country,
        first_event_date
    FROM raw_dataset
    GROUP BY user_id, first_year_revenue, country, first_event_date
    """
    
    print("📊 Loading and merging all data...")
    master_data = pd.read_sql(target_query, engine)
    
    # Merge feature tables
    for table in feature_tables:
        try:
            table_data = pd.read_sql(f"SELECT * FROM {table}", engine)
            master_data = master_data.merge(table_data, on='user_id', how='left')
            print(f"   ✅ Merged {table}")
        except Exception as e:
            print(f"   ❌ Error with {table}: {str(e)}")
    
    print(f"✅ Final dataset: {len(master_data):,} users, {len(master_data.columns)} columns")
    
    # Identify categorical features
    categorical_features = []
    
    # Get all object/categorical columns
    object_cols = master_data.select_dtypes(include=['object']).columns.tolist()
    
    # Get boolean columns (often categorical)
    bool_cols = master_data.select_dtypes(include=['bool']).columns.tolist()
    
    # Get low-cardinality numeric columns (likely categorical)
    numeric_cols = master_data.select_dtypes(include=[np.number]).columns.tolist()
    low_card_numeric = []
    
    for col in numeric_cols:
        if col != 'first_year_revenue':  # Skip target
            unique_count = master_data[col].nunique()
            if unique_count <= 20:  # Low cardinality threshold
                low_card_numeric.append(col)
    
    categorical_features = object_cols + bool_cols + low_card_numeric
    
    # Remove identifiers and target
    exclude_cols = ['user_id', 'first_year_revenue']
    categorical_features = [col for col in categorical_features if col not in exclude_cols]
    
    print(f"\n🔍 Found {len(categorical_features)} categorical features:")
    print(f"   Object columns: {len(object_cols)}")
    print(f"   Boolean columns: {len(bool_cols)}")
    print(f"   Low-cardinality numeric: {len(low_card_numeric)}")
    
    # Analyze each categorical feature
    print(f"\n📊 DETAILED CATEGORICAL ANALYSIS:")
    print("="*80)
    
    categorical_analysis = []
    
    for feature in categorical_features:
        print(f"\n🏷️ {feature.upper()}:")
        print("-" * 50)
        
        try:
            # Basic stats
            unique_count = master_data[feature].nunique()
            null_count = master_data[feature].isnull().sum()
            null_pct = (null_count / len(master_data)) * 100
            
            print(f"   Unique values: {unique_count}")
            print(f"   Null values: {null_count:,} ({null_pct:.2f}%)")
            
            # Skip if too many nulls or too many unique values
            if null_pct > 50:
                print(f"   ❌ SKIP: Too many nulls ({null_pct:.1f}%)")
                continue
                
            if unique_count > 100:
                print(f"   ❌ SKIP: Too many categories ({unique_count})")
                continue
            
            # Calculate LTV by category
            ltv_by_category = master_data.groupby(feature)['first_year_revenue'].agg([
                'count', 'mean', 'median', 'std'
            ]).reset_index()
            
            ltv_by_category.columns = [feature, 'count', 'mean_ltv', 'median_ltv', 'std_ltv']
            ltv_by_category = ltv_by_category.sort_values('mean_ltv', ascending=False)
            
            # Calculate variance in LTV across categories
            ltv_variance = ltv_by_category['mean_ltv'].var()
            ltv_range = ltv_by_category['mean_ltv'].max() - ltv_by_category['mean_ltv'].min()
            
            # Statistical significance test (ANOVA)
            categories = []
            ltv_groups = []
            
            for cat in master_data[feature].dropna().unique():
                cat_ltv = master_data[master_data[feature] == cat]['first_year_revenue'].values
                if len(cat_ltv) > 10:  # Minimum sample size
                    categories.append(cat)
                    ltv_groups.append(cat_ltv)
            
            if len(ltv_groups) >= 2:
                try:
                    f_stat, p_value = f_oneway(*ltv_groups)
                    is_significant = p_value < 0.05
                except:
                    f_stat, p_value, is_significant = 0, 1, False
            else:
                f_stat, p_value, is_significant = 0, 1, False
            
            # Calculate predictive power score
            paying_users_pct = (master_data['first_year_revenue'] > 0).mean() * 100
            
            category_paying_rates = []
            for cat in ltv_by_category[feature]:
                cat_data = master_data[master_data[feature] == cat]
                if len(cat_data) > 0:
                    paying_rate = (cat_data['first_year_revenue'] > 0).mean() * 100
                    category_paying_rates.append(paying_rate)
            
            paying_rate_variance = np.var(category_paying_rates) if category_paying_rates else 0
            
            print(f"   LTV Range: ${ltv_by_category['mean_ltv'].min():.2f} - ${ltv_by_category['mean_ltv'].max():.2f}")
            print(f"   LTV Variance: {ltv_variance:.4f}")
            print(f"   Statistical significance: {'✅' if is_significant else '❌'} (p={p_value:.4f})")
            print(f"   Paying rate variance: {paying_rate_variance:.2f}")
            
            # Show top categories
            print(f"   Top categories by LTV:")
            for i, row in ltv_by_category.head(5).iterrows():
                cat_name = str(row[feature])[:20]  # Truncate long names
                print(f"      {cat_name:<20}: ${row['mean_ltv']:>8.2f} (n={row['count']:,})")
            
            # Determine feature quality
            quality_score = 0
            
            # Scoring criteria
            if is_significant:
                quality_score += 3
            if ltv_variance > 1:
                quality_score += 2
            if ltv_range > 2:
                quality_score += 2
            if paying_rate_variance > 5:
                quality_score += 2
            if unique_count >= 3 and unique_count <= 20:
                quality_score += 1
            if null_pct < 10:
                quality_score += 1
            
            # Classify feature
            if quality_score >= 7:
                quality = "🥇 EXCELLENT"
            elif quality_score >= 5:
                quality = "🥈 GOOD"
            elif quality_score >= 3:
                quality = "🥉 FAIR"
            else:
                quality = "❌ POOR"
            
            print(f"   Quality: {quality} (Score: {quality_score}/11)")
            
            # Store analysis
            categorical_analysis.append({
                'feature': feature,
                'unique_count': unique_count,
                'null_pct': null_pct,
                'ltv_variance': ltv_variance,
                'ltv_range': ltv_range,
                'p_value': p_value,
                'is_significant': is_significant,
                'paying_rate_variance': paying_rate_variance,
                'quality_score': quality_score,
                'quality': quality,
                'top_category_ltv': ltv_by_category.iloc[0]['mean_ltv'],
                'sample_size': len(master_data[master_data[feature].notna()])
            })
            
        except Exception as e:
            print(f"   ❌ Error analyzing {feature}: {str(e)}")
    
    # Summary and recommendations
    print(f"\n🎯 CATEGORICAL FEATURE RECOMMENDATIONS:")
    print("="*80)
    
    # Convert to DataFrame for easier analysis
    analysis_df = pd.DataFrame(categorical_analysis)
    analysis_df = analysis_df.sort_values('quality_score', ascending=False)
    
    # Tier 1: Excellent features
    tier1_features = analysis_df[analysis_df['quality_score'] >= 7]['feature'].tolist()
    print(f"\n🥇 TIER 1 - MUST HAVE ({len(tier1_features)} features):")
    for i, feature in enumerate(tier1_features, 1):
        row = analysis_df[analysis_df['feature'] == feature].iloc[0]
        print(f"   {i:2d}. {feature:<30}: Score={row['quality_score']}, Range=${row['ltv_range']:.2f}, p={row['p_value']:.4f}")
    
    # Tier 2: Good features
    tier2_features = analysis_df[
        (analysis_df['quality_score'] >= 5) & 
        (analysis_df['quality_score'] < 7)
    ]['feature'].tolist()
    print(f"\n🥈 TIER 2 - GOOD TO HAVE ({len(tier2_features)} features):")
    for i, feature in enumerate(tier2_features, 1):
        row = analysis_df[analysis_df['feature'] == feature].iloc[0]
        print(f"   {i:2d}. {feature:<30}: Score={row['quality_score']}, Range=${row['ltv_range']:.2f}, p={row['p_value']:.4f}")
    
    # Tier 3: Fair features
    tier3_features = analysis_df[
        (analysis_df['quality_score'] >= 3) & 
        (analysis_df['quality_score'] < 5)
    ]['feature'].tolist()
    print(f"\n🥉 TIER 3 - CONSIDER ({len(tier3_features)} features):")
    for i, feature in enumerate(tier3_features[:5], 1):  # Show top 5
        row = analysis_df[analysis_df['feature'] == feature].iloc[0]
        print(f"   {i:2d}. {feature:<30}: Score={row['quality_score']}, Range=${row['ltv_range']:.2f}, p={row['p_value']:.4f}")
    
    # Final recommendation
    recommended_categorical = tier1_features + tier2_features
    
    print(f"\n📋 FINAL CATEGORICAL FEATURE RECOMMENDATION:")
    print("="*80)
    print(f"Recommended categorical features ({len(recommended_categorical)}):")
    
    for i, feature in enumerate(recommended_categorical, 1):
        row = analysis_df[analysis_df['feature'] == feature].iloc[0]
        print(f"   {i:2d}. {feature}")
    
    # Save results
    analysis_df.to_csv('categorical_features_analysis.csv', index=False)
    
    # Create feature selection summary
    feature_selection = {
        'tier1_excellent': tier1_features,
        'tier2_good': tier2_features,
        'tier3_fair': tier3_features,
        'recommended': recommended_categorical
    }
    
    import json
    with open('categorical_feature_selection.json', 'w') as f:
        json.dump(feature_selection, f, indent=2)
    
    print(f"\n💾 Saved results:")
    print(f"   - categorical_features_analysis.csv")
    print(f"   - categorical_feature_selection.json")
    
    return recommended_categorical, analysis_df

if __name__ == "__main__":
    recommended_features, analysis = analyze_categorical_features()
