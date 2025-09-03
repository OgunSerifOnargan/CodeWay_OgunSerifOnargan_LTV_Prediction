import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr
from sklearn.preprocessing import LabelEncoder
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings
warnings.filterwarnings('ignore')

# Database configuration
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def analyze_multicollinearity():
    """Analyze multicollinearity among selected features"""
    
    print("🔍 ANALYZING MULTICOLLINEARITY FOR FEATURE SELECTION...")
    engine = create_engine(DB_URL)
    
    # Load all data
    print("📊 Loading complete dataset...")
    
    # Get target data
    target_query = """
    SELECT 
        user_id,
        first_year_revenue,
        country,
        first_event_date
    FROM raw_dataset
    GROUP BY user_id, first_year_revenue, country, first_event_date
    LIMIT 100000
    """
    
    master_data = pd.read_sql(target_query, engine)
    
    # Merge feature tables
    feature_tables = [
        'post_subscription_features', 
        'pre_subscription_features',
        'revenue_features',
        'rfm_features',
        'training_table'
    ]
    
    for table in feature_tables:
        try:
            table_data = pd.read_sql(f"SELECT * FROM {table}", engine)
            master_data = master_data.merge(table_data, on='user_id', how='left')
            print(f"   ✅ Merged {table}")
        except Exception as e:
            print(f"   ❌ Error with {table}: {str(e)}")
    
    print(f"✅ Sample dataset: {len(master_data):,} users, {len(master_data.columns)} columns")
    
    # Define selected features from previous analysis
    
    # TOP NUMERICAL FEATURES (Tier 1 + Tier 2)
    numerical_features = [
        # Ultra High Impact (>0.5 correlation)
        'post_sub_revenue_efficiency',      # 0.617
        'post_sub_retention_score',         # 0.605
        'renewals_15d',                     # 0.593
        'renewal_revenue_impact',           # 0.587
        'renewal_to_subscribe_ratio',       # 0.583
        'renewal_count_post_sub',           # 0.582
        'post_sub_total_revenue',           # 0.573
        'subscriptions_started_15d',        # 0.507
        
        # High Impact (0.4-0.5 correlation)
        'retention_confidence_score',       # 0.506
        'days_since_last_subscribe',        # 0.500
        'trial_to_subscribe_ratio',         # 0.497
        'pre_sub_pattern_length',          # 0.496
        'pattern_complexity_score',        # 0.494
        'paywall_conversion_ratio',        # 0.493
        'subscription_count_total',        # 0.487
        'first_15_days_revenue_per_day',   # 0.455
        'first_15_days_total_revenue',     # 0.455
        'time_to_first_subscribe',         # 0.436
        'trial_to_subscribe_delay',        # 0.436
        'days_to_first_revenue',           # 0.421
        
        # Medium Impact
        'post_sub_event_diversity',        # 0.410
        'revenue_volatility_in_first_15_days', # 0.406
        'revenue_concentration_in_first_15_days', # 0.388
        'pre_sub_events_count',            # 0.359
        'first_15_days_avg_revenue_per_event', # 0.334
        'revenue_efficiency_in_first_15_days', # 0.321
        'post_sub_events_count',           # 0.320
        'post_sub_pattern_length',         # 0.320
        'days_since_trial_start',          # 0.267
        'day_of_free_trial_start',         # 0.199
        'rfm_score'                        # 0.145
    ]
    
    # TOP CATEGORICAL FEATURES (Tier 1 + Tier 2)
    categorical_features = [
        # Tier 1 - Excellent
        'rfm_segment',
        'has_golden_pattern',
        'country_tier',
        'free_trial_started',
        'is_trial_user',
        'is_subscriber',
        'revenue_pattern_risk_in_first_15_days',
        
        # Tier 2 - Good
        'is_churned',
        'is_refunded',
        'has_refund_in_first_15_days'
    ]
    
    print(f"\n📋 ANALYZING FEATURES:")
    print(f"   Numerical: {len(numerical_features)} features")
    print(f"   Categorical: {len(categorical_features)} features")
    
    # Step 1: Check availability and prepare data
    print(f"\n🔍 CHECKING FEATURE AVAILABILITY:")
    print("="*60)
    
    available_numerical = []
    available_categorical = []
    
    for feature in numerical_features:
        if feature in master_data.columns:
            available_numerical.append(feature)
            print(f"   ✅ {feature}")
        else:
            print(f"   ❌ {feature} (not found)")
    
    for feature in categorical_features:
        if feature in master_data.columns:
            available_categorical.append(feature)
            print(f"   ✅ {feature}")
        else:
            print(f"   ❌ {feature} (not found)")
    
    print(f"\n✅ Available: {len(available_numerical)} numerical + {len(available_categorical)} categorical")
    
    # Step 2: Prepare data for correlation analysis
    print(f"\n📊 PREPARING DATA FOR CORRELATION ANALYSIS:")
    print("="*60)
    
    # Create analysis dataset
    analysis_features = available_numerical + available_categorical
    analysis_data = master_data[analysis_features + ['first_year_revenue']].copy()
    
    # Handle missing values
    print("   Handling missing values...")
    for col in analysis_data.columns:
        if analysis_data[col].dtype in ['object', 'bool']:
            analysis_data[col] = analysis_data[col].fillna('missing')
        else:
            analysis_data[col] = analysis_data[col].fillna(0)
    
    # Encode categorical variables
    print("   Encoding categorical variables...")
    label_encoders = {}
    
    for feature in available_categorical:
        if feature in analysis_data.columns:
            le = LabelEncoder()
            analysis_data[f'{feature}_encoded'] = le.fit_transform(analysis_data[feature].astype(str))
            label_encoders[feature] = le
            print(f"      {feature}: {len(le.classes_)} categories")
    
    # Prepare final feature matrix
    final_numerical = available_numerical + [f'{f}_encoded' for f in available_categorical]
    X = analysis_data[final_numerical]
    y = analysis_data['first_year_revenue']
    
    print(f"   Final feature matrix: {X.shape}")
    
    # Step 3: Correlation Matrix Analysis
    print(f"\n🔗 CORRELATION MATRIX ANALYSIS:")
    print("="*60)
    
    correlation_matrix = X.corr()
    
    # Find high correlations (excluding diagonal)
    high_correlations = []
    
    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            corr_val = correlation_matrix.iloc[i, j]
            if abs(corr_val) > 0.7:  # High correlation threshold
                high_correlations.append({
                    'feature1': correlation_matrix.columns[i],
                    'feature2': correlation_matrix.columns[j],
                    'correlation': corr_val,
                    'abs_correlation': abs(corr_val)
                })
    
    high_correlations = sorted(high_correlations, key=lambda x: x['abs_correlation'], reverse=True)
    
    print(f"Found {len(high_correlations)} high correlations (|r| > 0.7):")
    
    if high_correlations:
        for i, corr in enumerate(high_correlations[:15], 1):  # Top 15
            print(f"   {i:2d}. {corr['feature1']:<35} ↔ {corr['feature2']:<35}: {corr['correlation']:>7.4f}")
    else:
        print("   ✅ No high correlations found!")
    
    # Step 4: VIF Analysis (for numerical features only)
    print(f"\n📈 VIF (VARIANCE INFLATION FACTOR) ANALYSIS:")
    print("="*60)
    
    # Use only numerical features for VIF
    X_numerical = analysis_data[available_numerical].fillna(0)
    
    # Remove features with zero variance
    non_zero_var_features = []
    for col in X_numerical.columns:
        if X_numerical[col].var() > 0:
            non_zero_var_features.append(col)
    
    X_numerical = X_numerical[non_zero_var_features]
    
    print(f"   Analyzing {len(X_numerical.columns)} numerical features...")
    
    vif_data = []
    
    try:
        for i, feature in enumerate(X_numerical.columns):
            vif_value = variance_inflation_factor(X_numerical.values, i)
            vif_data.append({
                'feature': feature,
                'vif': vif_value
            })
            
        vif_df = pd.DataFrame(vif_data).sort_values('vif', ascending=False)
        
        print("   VIF Results (VIF > 5 indicates multicollinearity):")
        for _, row in vif_df.head(15).iterrows():
            status = "🚨 HIGH" if row['vif'] > 10 else "⚠️ MEDIUM" if row['vif'] > 5 else "✅ LOW"
            print(f"      {row['feature']:<35}: {row['vif']:>8.2f} {status}")
            
    except Exception as e:
        print(f"   ❌ VIF calculation failed: {str(e)}")
        vif_df = pd.DataFrame()
    
    # Step 5: Feature Selection Recommendations
    print(f"\n🎯 MULTICOLLINEARITY-BASED FEATURE SELECTION:")
    print("="*60)
    
    # Identify problematic features
    problematic_pairs = []
    
    if high_correlations:
        print("   🚨 HIGH CORRELATION PAIRS TO RESOLVE:")
        
        for corr in high_correlations:
            feat1 = corr['feature1'].replace('_encoded', '')
            feat2 = corr['feature2'].replace('_encoded', '')
            
            # Get individual correlation with target
            if feat1 in analysis_data.columns:
                corr1_target = analysis_data[feat1].corr(y) if pd.api.types.is_numeric_dtype(analysis_data[feat1]) else 0
            else:
                corr1_target = 0
                
            if feat2 in analysis_data.columns:
                corr2_target = analysis_data[feat2].corr(y) if pd.api.types.is_numeric_dtype(analysis_data[feat2]) else 0
            else:
                corr2_target = 0
            
            # Recommend which feature to keep
            if abs(corr1_target) > abs(corr2_target):
                keep, drop = feat1, feat2
                keep_corr, drop_corr = corr1_target, corr2_target
            else:
                keep, drop = feat2, feat1
                keep_corr, drop_corr = corr2_target, corr1_target
            
            problematic_pairs.append({
                'keep': keep,
                'drop': drop,
                'pair_correlation': corr['correlation'],
                'keep_target_corr': keep_corr,
                'drop_target_corr': drop_corr
            })
            
            print(f"      KEEP: {keep:<35} (r_target={keep_corr:>6.3f})")
            print(f"      DROP: {drop:<35} (r_target={drop_corr:>6.3f})")
            print(f"      Pair correlation: {corr['correlation']:>6.3f}")
            print()
    
    # High VIF features
    high_vif_features = []
    if not vif_df.empty:
        high_vif_features = vif_df[vif_df['vif'] > 10]['feature'].tolist()
        
        if high_vif_features:
            print("   🚨 HIGH VIF FEATURES (VIF > 10) TO CONSIDER REMOVING:")
            for feature in high_vif_features:
                vif_val = vif_df[vif_df['feature'] == feature]['vif'].iloc[0]
                target_corr = analysis_data[feature].corr(y) if feature in analysis_data.columns else 0
                print(f"      {feature:<35}: VIF={vif_val:>8.2f}, r_target={target_corr:>6.3f}")
    
    # Step 6: Final Feature Recommendations
    print(f"\n📋 FINAL FEATURE SELECTION RECOMMENDATIONS:")
    print("="*60)
    
    # Start with all available features
    recommended_features = {
        'numerical': available_numerical.copy(),
        'categorical': available_categorical.copy()
    }
    
    # Remove features based on multicollinearity
    features_to_drop = set()
    
    # Drop features from high correlation pairs
    for pair in problematic_pairs:
        features_to_drop.add(pair['drop'])
    
    # Drop high VIF features (but keep if they have very high target correlation)
    for feature in high_vif_features:
        if feature in analysis_data.columns:
            target_corr = analysis_data[feature].corr(y)
            if abs(target_corr) < 0.4:  # Only drop if target correlation is not very high
                features_to_drop.add(feature)
    
    # Update recommendations
    recommended_features['numerical'] = [f for f in recommended_features['numerical'] if f not in features_to_drop]
    recommended_features['categorical'] = [f for f in recommended_features['categorical'] if f not in features_to_drop]
    
    print(f"ORIGINAL FEATURES:")
    print(f"   Numerical: {len(available_numerical)}")
    print(f"   Categorical: {len(available_categorical)}")
    print(f"   Total: {len(available_numerical) + len(available_categorical)}")
    
    print(f"\nFEATURES TO DROP DUE TO MULTICOLLINEARITY:")
    for feature in sorted(features_to_drop):
        print(f"   ❌ {feature}")
    
    print(f"\nFINAL RECOMMENDED FEATURES:")
    print(f"   Numerical ({len(recommended_features['numerical'])}):")
    for i, feature in enumerate(recommended_features['numerical'], 1):
        target_corr = analysis_data[feature].corr(y) if feature in analysis_data.columns else 0
        print(f"      {i:2d}. {feature:<35} (r_target={target_corr:>6.3f})")
    
    print(f"\n   Categorical ({len(recommended_features['categorical'])}):")
    for i, feature in enumerate(recommended_features['categorical'], 1):
        print(f"      {i:2d}. {feature}")
    
    print(f"\n   TOTAL RECOMMENDED: {len(recommended_features['numerical']) + len(recommended_features['categorical'])} features")
    
    # Save results
    results = {
        'high_correlations': high_correlations,
        'vif_results': vif_df.to_dict('records') if not vif_df.empty else [],
        'problematic_pairs': problematic_pairs,
        'features_to_drop': list(features_to_drop),
        'final_recommendations': recommended_features
    }
    
    import json
    with open('multicollinearity_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save correlation matrix
    correlation_matrix.to_csv('feature_correlation_matrix.csv')
    
    if not vif_df.empty:
        vif_df.to_csv('vif_analysis.csv', index=False)
    
    print(f"\n💾 SAVED RESULTS:")
    print(f"   - multicollinearity_analysis.json")
    print(f"   - feature_correlation_matrix.csv")
    if not vif_df.empty:
        print(f"   - vif_analysis.csv")
    
    return recommended_features, features_to_drop, high_correlations

if __name__ == "__main__":
    recommendations, dropped_features, correlations = analyze_multicollinearity()
