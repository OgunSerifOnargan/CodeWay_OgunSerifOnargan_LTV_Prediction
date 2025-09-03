#!/usr/bin/env python3
"""
LTV Prediction Pipeline - Master Execution Script

This script runs the complete LTV prediction pipeline in the correct order.
Run this script to execute the entire pipeline from raw data to final predictions.

Usage:
    python run_full_pipeline.py [--skip-eda] [--skip-cleaning] [--skip-features] [--skip-training]
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path

def run_script(script_path, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"📄 Running: {script_path}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                              check=True, 
                              capture_output=True, 
                              text=True)
        
        elapsed = time.time() - start_time
        print(f"✅ SUCCESS ({elapsed:.1f}s): {description}")
        
        # Print last few lines of output if available
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 3:
                print("📊 Output (last 3 lines):")
                for line in lines[-3:]:
                    print(f"   {line}")
            else:
                print(f"📊 Output: {result.stdout.strip()}")
                
        return True
        
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"❌ FAILED ({elapsed:.1f}s): {description}")
        print(f"Error: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ ERROR ({elapsed:.1f}s): {description}")
        print(f"Exception: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run LTV Prediction Pipeline')
    parser.add_argument('--skip-eda', action='store_true', help='Skip EDA steps')
    parser.add_argument('--skip-cleaning', action='store_true', help='Skip data cleaning steps')
    parser.add_argument('--skip-features', action='store_true', help='Skip feature creation steps')
    parser.add_argument('--skip-training', action='store_true', help='Skip model training steps')
    
    args = parser.parse_args()
    
    pipeline_dir = Path(__file__).parent
    
    print("🎯 LTV PREDICTION PIPELINE")
    print("=" * 60)
    print(f"📁 Pipeline Directory: {pipeline_dir}")
    print(f"🐍 Python: {sys.executable}")
    print(f"⏰ Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track pipeline progress
    total_steps = 0
    completed_steps = 0
    failed_steps = 0
    
    # Step 1: Data Cleaning
    if not args.skip_cleaning:
        print(f"\n{'#'*60}")
        print("📥 PHASE 1: DATA CLEANING & PREPARATION")
        print(f"{'#'*60}")
        
        cleaning_scripts = [
            ("data_cleaning/load_parquet_to_postgres_chunked.py", "Load parquet data to PostgreSQL"),
            ("data_cleaning/handle_null_values_simple.py", "Handle NULL values"),
            # Removed remove_extra_columns.py as it's unnecessary
        ]
        
        for script, desc in cleaning_scripts:
            total_steps += 1
            script_path = pipeline_dir / script
            if script_path.exists():
                if run_script(script_path, desc):
                    completed_steps += 1
                else:
                    failed_steps += 1
                    print(f"⚠️  Continuing pipeline despite failure in {script}")
            else:
                print(f"⚠️  Script not found: {script_path}")
                failed_steps += 1
    
    # Step 2: EDA (Optional)
    if not args.skip_eda:
        print(f"\n{'#'*60}")
        print("🔍 PHASE 2: EXPLORATORY DATA ANALYSIS (Optional)")
        print(f"{'#'*60}")
        
        eda_scripts = [
            ("EDA/analyze_null_values.py", "Analyze NULL value patterns"),
            ("EDA/check_data_timespan.py", "Check temporal data coverage"),
            ("EDA/analyze_event_names.py", "Analyze event name patterns"),
            ("EDA/analyze_multicollinearity.py", "Analyze feature correlations"),
            ("EDA/analyze_categorical_features.py", "Analyze categorical features"),
            ("EDA/analyze_country_revenue_clustering.py", "Analyze country clustering"),
            ("EDA/analyze_15_day_revenue_timeline.py", "Analyze revenue timeline"),
            ("EDA/analyze_paywall_revenue.py", "Analyze paywall revenue"),
            ("EDA/analyze_time_patterns.py", "Analyze time patterns"),
            ("EDA/analyze_high_revenue_user_patterns.py", "Analyze high revenue patterns"),
        ]
        
        for script, desc in eda_scripts:
            total_steps += 1
            script_path = pipeline_dir / script
            if script_path.exists():
                if run_script(script_path, desc):
                    completed_steps += 1
                else:
                    failed_steps += 1
                    print(f"⚠️  Continuing pipeline despite EDA failure in {script}")
            else:
                print(f"⚠️  Script not found: {script_path}")
                failed_steps += 1
    
    # Step 3: Feature Engineering
    if not args.skip_features:
        print(f"\n{'#'*60}")
        print("🔧 PHASE 3: FEATURE ENGINEERING")
        print(f"{'#'*60}")
        
        feature_scripts = [
            ("feature_creation/create_revenue_features_parallel.py", "Create revenue features"),
            ("feature_creation/create_post_subscription_features_table.py", "Create post-subscription features"),
            ("feature_creation/create_pre_subscription_features_ultra_fast.py", "Create pre-subscription features"),
            ("feature_creation/create_rfm_features_table.py", "Create RFM features"),
            ("feature_creation/create_country_revenue_features_15days.py", "Create country features"),
            ("feature_creation/create_event_name_features_parallel.py", "Create event name features"),
            ("feature_creation/create_non_paying_features_fast.py", "Create non-paying user features"),
            ("feature_creation/consolidate_features.py", "Consolidate all features"),
        ]
        
        for script, desc in feature_scripts:
            total_steps += 1
            script_path = pipeline_dir / script
            if script_path.exists():
                if run_script(script_path, desc):
                    completed_steps += 1
                else:
                    failed_steps += 1
                    print(f"❌ CRITICAL: Feature creation failed in {script}")
                    print("🛑 Stopping pipeline - features are required for training")
                    break
            else:
                print(f"⚠️  Script not found: {script_path}")
                failed_steps += 1
    
    # Step 4: Model Training
    if not args.skip_training and failed_steps == 0:
        print(f"\n{'#'*60}")
        print("🤖 PHASE 4: MODEL TRAINING & PREDICTION")
        print(f"{'#'*60}")
        
        training_scripts = [
            ("model_training/prepare_dataset.py", "Prepare training dataset"),
            ("model_training/train_models.py", "Train ML models"),
            ("model_training/predict_ltv.py", "Generate predictions"),
            ("model_training/save_test_results.py", "Save predictions to database"),
            ("model_training/generate_evaluation_report.py", "Generate evaluation report"),
        ]
        
        for script, desc in training_scripts:
            total_steps += 1
            script_path = pipeline_dir / script
            if script_path.exists():
                if run_script(script_path, desc):
                    completed_steps += 1
                else:
                    failed_steps += 1
                    print(f"❌ CRITICAL: Training failed in {script}")
                    break
            else:
                print(f"⚠️  Script not found: {script_path}")
                failed_steps += 1
    
    # Final Summary
    print(f"\n{'='*60}")
    print("🏁 PIPELINE EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"📊 Total Steps: {total_steps}")
    print(f"✅ Completed: {completed_steps}")
    print(f"❌ Failed: {failed_steps}")
    print(f"📈 Success Rate: {(completed_steps/total_steps*100) if total_steps > 0 else 0:.1f}%")
    print(f"⏰ End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed_steps == 0:
        print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("📋 Check the following for results:")
        print("   - Database tables with features and predictions")
        print("   - Model files in model_training/results/")
        print("   - Evaluation reports in final/")
        return 0
    else:
        print(f"\n⚠️  PIPELINE COMPLETED WITH {failed_steps} FAILURES")
        print("🔧 Check the error messages above and fix issues")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
