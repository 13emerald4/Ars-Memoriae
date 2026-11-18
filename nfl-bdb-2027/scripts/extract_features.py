"""
extract_features.py
Extracts 10 Hz kinematic derivatives and Newtonian features across WR, DB, DL, and OL cohorts.
"""
import os
import polars as pl
import statsmodels.api as sm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "nfl-big-data-bowl-2027")
OUT_DIR = os.path.join(BASE_DIR, "data")

def extract_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Loading raw Combine tracking and metadata...")
    comb_trk = pl.read_csv(os.path.join(DATA_DIR, "combine_tracking.csv"))
    players = pl.read_csv(os.path.join(DATA_DIR, "players.csv"), null_values=["NA"])
    comb_res = pl.read_csv(os.path.join(DATA_DIR, "combine_results.csv"), null_values=["NA"])
    success = pl.read_csv(os.path.join(DATA_DIR, "player_career_successes.csv"))

    # 1. Wide Receivers (In-Cut Velocity Preservation)
    print("Extracting WR cutting kinematics...")
    wr_ids = players.filter(pl.col("nfl_position") == "WR")["nfl_id"].to_list()
    cutting_drills = ["CURL_ROUTE_RIGHT", "COMEBACK_ROUTE_RIGHT", "SPEED_OUT_ROUTE_LEFT", "SLANT_ROUTE_LEFT"]
    wr_cuts = comb_trk.filter((pl.col("nfl_id").is_in(wr_ids)) & 
                              (pl.col("drill_name").is_in(cutting_drills)) & 
                              (pl.col("entity_type") == "PLAYER"))
    wr_cuts = wr_cuts.with_columns([
        ((pl.col("s") - pl.col("s").shift(1)) / 0.1).alias("delta_s_dt")
    ])
    wr_feat = wr_cuts.group_by("nfl_id").agg([
        (pl.col("s") * 3.29184).quantile(0.50).alias("wr_median_cut_speed"),
        (pl.col("s") * 3.29184).quantile(0.90).alias("wr_p90_cut_speed"),
        pl.col("delta_s_dt").quantile(0.05).alias("wr_p05_braking_decel"),
        (pl.col("s") * 3.29184).max().alias("wr_max_drill_speed")
    ])
    df_wr = wr_feat.join(comb_res, on="nfl_id").join(success, on="nfl_id").join(players, on="nfl_id")
    print(f"WR cohort: {len(df_wr)} prospects")

    # 2. Defensive Backs (Transition Break Speed)
    print("Extracting DB transition break kinematics...")
    db_ids = players.filter(pl.col("nfl_position").is_in(["CB", "SS", "FS", "DB"]))["nfl_id"].to_list()
    db_drills = comb_trk.filter((pl.col("nfl_id").is_in(db_ids)) & 
                                (pl.col("drill_name") == "BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION") &
                                (pl.col("entity_type") == "PLAYER"))
    db_feat = db_drills.group_by("nfl_id").agg([
        (pl.col("s") * 3.29184).quantile(0.50).alias("db_median_speed"),
        (pl.col("s") * 3.29184).quantile(0.90).alias("db_p90_speed"),
        (pl.col("a") * 3.29184).quantile(0.90).alias("db_p90_accel"),
        (pl.col("s") * 3.29184).max().alias("db_max_speed")
    ])
    df_db = db_feat.join(comb_res, on="nfl_id").join(success, on="nfl_id").join(players, on="nfl_id")
    print(f"DB cohort: {len(df_db)} prospects")

    # 3. Defensive Line / EDGE (Mass-Residualized Acceleration Gamma_OE)
    print("Extracting DL/EDGE trench acceleration...")
    dl_ids = players.filter(pl.col("nfl_position").is_in(["DE", "DT", "NT", "OLB"]))["nfl_id"].to_list()
    dl_drills = comb_trk.filter((pl.col("nfl_id").is_in(dl_ids)) & (pl.col("entity_type") == "PLAYER"))
    dl_feat = dl_drills.group_by("nfl_id").agg([
        (pl.col("a") * 3.29184).quantile(0.90).alias("dl_gamma_accel"),
        (pl.col("s") * 3.29184).max().alias("dl_max_speed")
    ])
    df_dl = dl_feat.join(comb_res, on="nfl_id").join(success, on="nfl_id").join(players, on="nfl_id")
    df_dl_clean = df_dl.filter(pl.col("combine_weight").is_not_null() & pl.col("dl_gamma_accel").is_not_null()).to_pandas()
    mass_mod = sm.OLS(df_dl_clean["dl_gamma_accel"], sm.add_constant(df_dl_clean["combine_weight"])).fit()
    df_dl_clean["dl_gamma_oe"] = mass_mod.resid
    df_dl = pl.from_pandas(df_dl_clean)
    print(f"DL cohort: {len(df_dl)} prospects")

    # 4. Offensive Line (Lateral Mirror Gamma_OE)
    print("Extracting OL lateral mirror kinematics...")
    ol_ids = players.filter(pl.col("nfl_position").is_in(["T", "G", "C"]))["nfl_id"].to_list()
    ol_drills = comb_trk.filter((pl.col("nfl_id").is_in(ol_ids)) & 
                                (pl.col("drill_name").is_in(["PASS_PRO_MIRROR_DRILL", "PASS_PRO-MIRROR_DRILL", "FIVE_YARD_WAVE_DRILL_SLIDE_AND_SHUFFLE"])) &
                                (pl.col("entity_type") == "PLAYER"))
    ol_feat = ol_drills.group_by("nfl_id").agg([
        (pl.col("s") * 3.29184).quantile(0.50).alias("ol_median_speed"),
        (pl.col("s") * 3.29184).quantile(0.90).alias("ol_p90_speed"),
        (pl.col("a") * 3.29184).quantile(0.90).alias("ol_p90_accel"),
        (pl.col("s") * 3.29184).max().alias("ol_max_speed")
    ])
    df_ol = ol_feat.join(comb_res, on="nfl_id").join(success, on="nfl_id").join(players, on="nfl_id")
    df_ol_clean = df_ol.filter(pl.col("combine_weight").is_not_null() & pl.col("ol_p90_accel").is_not_null()).to_pandas()
    mass_mod_ol = sm.OLS(df_ol_clean["ol_p90_accel"], sm.add_constant(df_ol_clean["combine_weight"])).fit()
    df_ol_clean["ol_gamma_oe"] = mass_mod_ol.resid
    df_ol = pl.from_pandas(df_ol_clean)
    print(f"OL cohort: {len(df_ol)} prospects")

    # Save to disk
    df_wr.write_parquet(os.path.join(OUT_DIR, "features_wr.parquet"))
    df_db.write_parquet(os.path.join(OUT_DIR, "features_db.parquet"))
    df_dl.write_parquet(os.path.join(OUT_DIR, "features_dl.parquet"))
    df_ol.write_parquet(os.path.join(OUT_DIR, "features_ol.parquet"))

    df_wr.write_csv(os.path.join(OUT_DIR, "features_wr.csv"))
    df_db.write_csv(os.path.join(OUT_DIR, "features_db.csv"))
    df_dl.write_csv(os.path.join(OUT_DIR, "features_dl.csv"))
    df_ol.write_csv(os.path.join(OUT_DIR, "features_ol.csv"))

    print("All features extracted and persisted successfully!")

if __name__ == "__main__":
    extract_all()
