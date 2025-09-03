import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import psycopg2
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings('ignore')

# Database connection
DB_URL = 'postgresql://ogunserifonargan@localhost:5432/lvp_database'

def get_country_revenue_data():
    """Get country-level revenue data for clustering"""
    try:
        engine = create_engine(DB_URL)
        
        # Get comprehensive country revenue statistics
        query = """
        SELECT 
            country,
            COUNT(*) as user_count,
            AVG(COALESCE(first_year_revenue, 0)) as avg_revenue,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY COALESCE(first_year_revenue, 0)) as median_revenue,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY COALESCE(first_year_revenue, 0)) as q25_revenue,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY COALESCE(first_year_revenue, 0)) as q75_revenue,
            STDDEV(COALESCE(first_year_revenue, 0)) as revenue_std,
            MIN(COALESCE(first_year_revenue, 0)) as min_revenue,
            MAX(COALESCE(first_year_revenue, 0)) as max_revenue,
            SUM(COALESCE(first_year_revenue, 0)) as total_revenue
        FROM raw_dataset
        WHERE country IS NOT NULL 
        AND country != ''
        GROUP BY country
        HAVING COUNT(*) >= 10  -- Minimum 10 users per country for statistical significance
        ORDER BY avg_revenue DESC
        """
        
        df = pd.read_sql(query, engine)
        engine.dispose()
        
        print(f"✅ Found {len(df)} countries with sufficient data")
        print(f"📊 Total users analyzed: {df['user_count'].sum():,}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error getting country revenue data: {e}")
        return None

def prepare_clustering_features(df):
    """Prepare features for clustering"""
    # Create clustering features
    clustering_df = df.copy()
    
    # Revenue-based features
    clustering_df['revenue_per_user'] = clustering_df['total_revenue'] / clustering_df['user_count']
    clustering_df['revenue_efficiency'] = clustering_df['avg_revenue'] / (clustering_df['revenue_std'] + 1e-6)  # Avoid division by zero
    
    # User distribution features
    clustering_df['user_percentage'] = clustering_df['user_count'] / clustering_df['user_count'].sum()
    
    # Revenue distribution features
    clustering_df['revenue_percentage'] = clustering_df['total_revenue'] / clustering_df['total_revenue'].sum()
    
    # Select features for clustering
    features = ['avg_revenue', 'median_revenue', 'revenue_per_user', 'revenue_efficiency', 'user_percentage']
    
    # Remove rows with infinite or NaN values
    clustering_df = clustering_df.replace([np.inf, -np.inf], np.nan).dropna(subset=features)
    
    print(f"✅ Prepared {len(clustering_df)} countries for clustering")
    print(f"🔍 Features used: {features}")
    
    return clustering_df, features

def perform_kmeans_clustering(df, features, max_k=7):
    """Perform K-means clustering and find optimal K"""
    # Prepare data for clustering
    X = df[features].values
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Test different K values
    k_values = range(2, max_k + 1)
    inertias = []
    silhouette_scores = []
    
    print(f"🔍 Testing K values from 2 to {max_k}...")
    
    for k in k_values:
        # Fit K-means
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        
        # Calculate metrics
        inertias.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(X_scaled, kmeans.labels_))
        
        print(f"   K={k}: Inertia={kmeans.inertia_:.2f}, Silhouette={silhouette_scores[-1]:.3f}")
    
    return k_values, inertias, silhouette_scores, X_scaled, scaler

def find_optimal_k(k_values, inertias, silhouette_scores):
    """Find optimal K using elbow method and silhouette analysis"""
    print("\n🎯 OPTIMAL K ANALYSIS:")
    
    # Elbow method
    print("📈 Elbow Method Analysis:")
    for i in range(1, len(k_values)):
        if i > 0:
            improvement = (inertias[i-1] - inertias[i]) / inertias[i-1]
            print(f"   K={k_values[i]}: Improvement = {improvement:.3f}")
    
    # Silhouette analysis
    print("\n📊 Silhouette Score Analysis:")
    best_silhouette_idx = np.argmax(silhouette_scores)
    print(f"   Best silhouette score: K={k_values[best_silhouette_idx]} ({silhouette_scores[best_silhouette_idx]:.3f})")
    
    # Recommend optimal K
    optimal_k = k_values[best_silhouette_idx]
    print(f"\n🎯 RECOMMENDED OPTIMAL K: {optimal_k}")
    
    return optimal_k

def create_final_clusters(df, features, optimal_k, X_scaled, scaler):
    """Create final clusters with optimal K"""
    print(f"\n🚀 Creating final clusters with K={optimal_k}...")
    
    # Fit final K-means
    final_kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    final_kmeans.fit(X_scaled)
    
    # Add cluster labels
    df_with_clusters = df.copy()
    df_with_clusters['cluster'] = final_kmeans.labels_
    
    # Analyze clusters
    cluster_analysis = df_with_clusters.groupby('cluster').agg({
        'country': 'count',
        'avg_revenue': ['mean', 'std'],
        'user_count': 'sum',
        'total_revenue': 'sum'
    }).round(2)
    
    cluster_analysis.columns = ['country_count', 'avg_revenue_mean', 'avg_revenue_std', 'total_users', 'total_revenue']
    
    print("\n📊 CLUSTER ANALYSIS:")
    print(cluster_analysis)
    
    # Sort clusters by average revenue
    cluster_ranking = df_with_clusters.groupby('cluster')['avg_revenue'].mean().sort_values(ascending=False)
    
    print("\n🏆 CLUSTER RANKING (by average revenue):")
    for rank, (cluster, avg_rev) in enumerate(cluster_ranking.items(), 1):
        tier = "HIGH" if rank == 1 else "MID" if rank == 2 else "LOW"
        print(f"   Rank {rank} (Cluster {cluster}): {tier} - Avg Revenue: ${avg_rev:.2f}")
    
    return df_with_clusters, final_kmeans

def visualize_clustering(df, k_values, inertias, silhouette_scores, df_with_clusters):
    """Create visualizations for clustering analysis"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Country Revenue Clustering Analysis for LTV Prediction', fontsize=16, fontweight='bold')
    
    # 1. Elbow plot
    axes[0, 0].plot(k_values, inertias, 'bo-', linewidth=2, markersize=8)
    axes[0, 0].set_xlabel('Number of Clusters (K)')
    axes[0, 0].set_ylabel('Inertia')
    axes[0, 0].set_title('Elbow Method for Optimal K')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Silhouette plot
    axes[0, 1].plot(k_values, silhouette_scores, 'ro-', linewidth=2, markersize=8)
    axes[0, 1].set_xlabel('Number of Clusters (K)')
    axes[0, 1].set_ylabel('Silhouette Score')
    axes[0, 1].set_title('Silhouette Analysis for Optimal K')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Cluster distribution
    cluster_counts = df_with_clusters['cluster'].value_counts().sort_index()
    axes[1, 0].bar(cluster_counts.index, cluster_counts.values, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
    axes[1, 0].set_xlabel('Cluster')
    axes[1, 0].set_ylabel('Number of Countries')
    axes[1, 0].set_title('Countries per Cluster')
    axes[1, 0].set_xticks(cluster_counts.index)
    
    # 4. Revenue distribution by cluster
    cluster_revenue = df_with_clusters.groupby('cluster')['avg_revenue'].mean().sort_values(ascending=False)
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    axes[1, 1].bar(range(len(cluster_revenue)), cluster_revenue.values, color=colors[:len(cluster_revenue)])
    axes[1, 1].set_xlabel('Cluster Rank')
    axes[1, 1].set_ylabel('Average Revenue ($)')
    axes[1, 1].set_title('Average Revenue by Cluster Rank')
    axes[1, 1].set_xticks(range(len(cluster_revenue)))
    axes[1, 1].set_xticklabels([f'Rank {i+1}' for i in range(len(cluster_revenue))])
    
    plt.tight_layout()
    plt.savefig('country_revenue_clustering_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📊 Visualization saved as 'country_revenue_clustering_analysis.png'")

def save_clustering_results(df_with_clusters, optimal_k):
    """Save clustering results to CSV and create summary"""
    # Save detailed results
    output_file = f'country_revenue_clusters_k{optimal_k}.csv'
    df_with_clusters.to_csv(output_file, index=False)
    print(f"💾 Detailed results saved to '{output_file}'")
    
    # Create summary report
    summary_file = f'country_clustering_summary_k{optimal_k}.md'
    
    with open(summary_file, 'w') as f:
        f.write(f"# Country Revenue Clustering Analysis for LTV Prediction\n\n")
        f.write(f"**Optimal K:** {optimal_k}\n\n")
        
        f.write("## Cluster Summary\n\n")
        cluster_summary = df_with_clusters.groupby('cluster').agg({
            'country': 'count',
            'avg_revenue': ['mean', 'std'],
            'user_count': 'sum',
            'total_revenue': 'sum'
        }).round(2)
        
        f.write(cluster_summary.to_string())
        f.write("\n\n## Country Distribution by Cluster\n\n")
        
        for cluster in sorted(df_with_clusters['cluster'].unique()):
            countries = df_with_clusters[df_with_clusters['cluster'] == cluster]['country'].tolist()
            f.write(f"**Cluster {cluster}:** {', '.join(countries)}\n\n")
    
    print(f"📝 Summary report saved to '{summary_file}'")

def main():
    """Main function to run country revenue clustering analysis"""
    print("🚀 COUNTRY REVENUE CLUSTERING ANALYSIS FOR LTV PREDICTION")
    print("=" * 70)
    
    # Step 1: Get country revenue data
    print("\n📊 Step 1: Getting country revenue data...")
    df = get_country_revenue_data()
    if df is None:
        return
    
    print(f"📈 Top 5 countries by average revenue:")
    print(df.head().to_string(index=False))
    
    # Step 2: Prepare clustering features
    print("\n🔧 Step 2: Preparing clustering features...")
    clustering_df, features = prepare_clustering_features(df)
    
    # Step 3: Perform K-means clustering
    print("\n🎯 Step 3: Performing K-means clustering...")
    k_values, inertias, silhouette_scores, X_scaled, scaler = perform_kmeans_clustering(clustering_df, features)
    
    # Step 4: Find optimal K
    print("\n🔍 Step 4: Finding optimal K...")
    optimal_k = find_optimal_k(k_values, inertias, silhouette_scores)
    
    # Step 5: Create final clusters
    print("\n🏗️ Step 5: Creating final clusters...")
    df_with_clusters, final_kmeans = create_final_clusters(clustering_df, features, optimal_k, X_scaled, scaler)
    
    # Step 6: Visualize results
    print("\n📊 Step 6: Creating visualizations...")
    visualize_clustering(df, k_values, inertias, silhouette_scores, df_with_clusters)
    
    # Step 7: Save results
    print("\n💾 Step 7: Saving results...")
    save_clustering_results(df_with_clusters, optimal_k)
    
    print("\n✅ COUNTRY REVENUE CLUSTERING ANALYSIS COMPLETED!")
    print("🎯 Next step: Integrate country tiers into LTV prediction model")

if __name__ == "__main__":
    main()
