"""
run_regressions.py
Runs frequentist OLS, Logit, and Welch's t-tests across WR, DB, DL, and OL cohorts.
"""
import os
import polars as pl
import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def run_models():
    print("=" * 80)
    print("1. WIDE RECEIVERS: In-Cut Velocity Preservation vs. 40-Yard Dash")
    print("=" * 80)
    df_wr = pl.read_parquet(os.path.join(DATA_DIR, "features_wr.parquet")).to_pandas()
    df_wr["starter"] = (df_wr["career_games_started"] >= 10).astype(int)
    clean_wr = df_wr.dropna(subset=["wr_median_cut_speed", "career_offensive_snaps", "forty"])

    # OLS: Snaps
    X_ols = sm.add_constant(clean_wr[["wr_median_cut_speed", "forty"]])
    y_ols = clean_wr["career_offensive_snaps"]
    mod_wr_ols = sm.OLS(y_ols, X_ols).fit()
    print("--- OLS: Career Offensive Snaps (WR) ---")
    print(mod_wr_ols.summary().tables[1])
    print(f"R-squared: {mod_wr_ols.rsquared:.3f}, N = {len(clean_wr)}")

    # Logit: Starter Odds
    mod_wr_logit = sm.Logit(clean_wr["starter"], X_ols).fit(disp=False)
    print("\n--- Logit: Starter Probability (WR) ---")
    print(mod_wr_logit.summary().tables[1])
    print(f"In-Cut Speed Odds Ratio: {np.exp(mod_wr_logit.params['wr_median_cut_speed']):.2f}x")

    # Welch's t-test: Starters vs Fringe
    top_wr = clean_wr[clean_wr["career_games_started"] >= 20]["wr_median_cut_speed"]
    fringe_wr = clean_wr[clean_wr["career_games_started"] <= 2]["wr_median_cut_speed"]
    t_stat, p_val = stats.ttest_ind(top_wr, fringe_wr, equal_var=False)
    d = (top_wr.mean() - fringe_wr.mean()) / np.sqrt((top_wr.var() + fringe_wr.var()) / 2)
    print(f"\nWelch's t-test (Top vs Fringe WR): t = {t_stat:.3f}, p = {p_val:.5f}, Cohen's d = {d:.2f}")

    print("\n" + "=" * 80)
    print("2. DEFENSIVE BACKS: Transition Break Speed vs. 40-Yard Dash")
    print("=" * 80)
    df_db = pl.read_parquet(os.path.join(DATA_DIR, "features_db.parquet")).to_pandas()
    clean_db = df_db.dropna(subset=["db_p90_speed", "career_defensive_snaps", "forty"])
    X_db = sm.add_constant(clean_db[["db_p90_speed", "forty"]])
    y_db = clean_db["career_defensive_snaps"]
    mod_db_ols = sm.OLS(y_db, X_db).fit()
    print("--- OLS: Career Defensive Snaps (DB) ---")
    print(mod_db_ols.summary().tables[1])
    print(f"R-squared: {mod_db_ols.rsquared:.3f}, N = {len(clean_db)}")

    print("\n" + "=" * 80)
    print("3. DEFENSIVE LINE / EDGE: Gamma-Over-Expected (Trench Acceleration)")
    print("=" * 80)
    df_dl = pl.read_parquet(os.path.join(DATA_DIR, "features_dl.parquet")).to_pandas()
    df_dl["starter"] = (df_dl["career_games_started"] >= 10).astype(int)
    clean_dl = df_dl.dropna(subset=["dl_gamma_oe", "combine_weight"])
    X_dl = sm.add_constant(clean_dl[["dl_gamma_oe", "combine_weight"]])
    mod_dl_logit = sm.Logit(clean_dl["starter"], X_dl).fit(disp=False)
    print("--- Logit: Starter Probability (DL/EDGE) ---")
    print(mod_dl_logit.summary().tables[1])
    print(f"Gamma_OE Odds Ratio: {np.exp(mod_dl_logit.params['dl_gamma_oe']):.2f}x, N = {len(clean_dl)}")

    print("\n" + "=" * 80)
    print("4. OFFENSIVE LINE: Gamma-Over-Expected (Lateral Mirror Acceleration)")
    print("=" * 80)
    df_ol = pl.read_parquet(os.path.join(DATA_DIR, "features_ol.parquet")).to_pandas()
    clean_ol = df_ol.dropna(subset=["ol_gamma_oe", "career_offensive_snaps", "forty"])
    X_ol = sm.add_constant(clean_ol[["ol_gamma_oe", "forty"]])
    y_ol = clean_ol["career_offensive_snaps"]
    mod_ol_ols = sm.OLS(y_ol, X_ol).fit()
    print("--- OLS: Career Offensive Snaps (OL) ---")
    print(mod_ol_ols.summary().tables[1])
    print(f"R-squared: {mod_ol_ols.rsquared:.3f}, N = {len(clean_ol)}")
    print("=" * 80)

if __name__ == "__main__":
    run_models()
