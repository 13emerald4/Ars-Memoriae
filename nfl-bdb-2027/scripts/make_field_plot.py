"""
make_field_plot.py
Generates the publication static figures:
1. route_kinematics_field_plot.png
2. wr_speed_pdf_cdf.png
3. mass_vs_gamma_scatter.png
"""
import os
import polars as pl
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats
import statsmodels.formula.api as smf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "nfl-big-data-bowl-2027")

def make_all_plots():
    print("Loading data for static figures...")
    comb = pl.read_csv(os.path.join(DATA_DIR, "combine_tracking.csv"))
    players = pl.read_csv(os.path.join(DATA_DIR, "players.csv"), null_values=["NA"])
    comb_res = pl.read_csv(os.path.join(DATA_DIR, "combine_results.csv"), null_values=["NA"])
    success = pl.read_csv(os.path.join(DATA_DIR, "player_career_successes.csv"))

    # -------------------------------------------------------------
    # 1. wr_speed_pdf_cdf.png
    # -------------------------------------------------------------
    print("Generating wr_speed_pdf_cdf.png...")
    players_to_plot = {
        56042: ("Puka Nacua (Pick 177, All-Pro)", "crimson"),
        55884: ("Jaxon Smith-Njigba (Pick 20, All-Pro)", "navy"),
        55885: ("Quentin Johnston (Pick 21)", "gray"),
        57144: ("Brian Thomas Jr. (Pick 23)", "teal")
    }

    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    for nfl_id, (label, color) in players_to_plot.items():
        s = comb.filter((pl.col("nfl_id") == nfl_id) & (pl.col("entity_type") == "PLAYER"))["s"].to_numpy()
        s_kmh = s * 3.29184
        kde = stats.gaussian_kde(s_kmh)
        x_grid = np.linspace(0, 38, 200)
        plt.plot(x_grid, kde(x_grid), label=label, color=color, lw=2.2)

    plt.axvspan(10, 26, color="yellow", alpha=0.15, label="NFL Core Working Band (10-26 km/h)")
    plt.title("Speed Probability Density Function (PDF) in Combine Drills")
    plt.xlabel("Speed (km/h)")
    plt.ylabel("Density")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    for nfl_id, (label, color) in players_to_plot.items():
        s = comb.filter((pl.col("nfl_id") == nfl_id) & (pl.col("entity_type") == "PLAYER"))["s"].to_numpy()
        s_kmh = np.sort(s * 3.29184)
        y_cdf = np.arange(1, len(s_kmh) + 1) / len(s_kmh)
        plt.plot(s_kmh, y_cdf, label=label, color=color, lw=2.2)

    plt.axvline(26, color="red", linestyle="--", alpha=0.6, label="Top-Speed Threshold (26 km/h)")
    plt.title("Speed Cumulative Distribution Function (CDF)")
    plt.xlabel("Speed (km/h)")
    plt.ylabel("Cumulative Probability F(s)")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    pdf_cdf_path = os.path.join(BASE_DIR, "wr_speed_pdf_cdf.png")
    plt.savefig(pdf_cdf_path, dpi=200)
    plt.close()
    print(f"Saved: {pdf_cdf_path}")

    # -------------------------------------------------------------
    # 2. route_kinematics_field_plot.png
    # -------------------------------------------------------------
    print("Generating route_kinematics_field_plot.png...")
    def draw_nfl_field_section(ax, xmin=20, xmax=45, ymin=0, ymax=15):
        ax.set_facecolor("#2d6a4f")
        for x in range(int(xmin // 5) * 5, int(xmax) + 6, 5):
            if xmin <= x <= xmax:
                lw = 1.8 if x % 10 == 0 else 0.9
                color = "white" if x % 10 == 0 else "#e0e0e0"
                alpha = 0.85 if x % 10 == 0 else 0.5
                ax.axvline(x, ymin=0, ymax=1, color=color, lw=lw, alpha=alpha, linestyle="-")
                if x % 10 == 0:
                    ax.text(x, ymax - 1.2, f"{x}", color="white", fontsize=11, fontweight="bold", ha="center", va="center", alpha=0.9)
                    ax.text(x, ymin + 1.2, f"{x}", color="white", fontsize=11, fontweight="bold", ha="center", va="center", alpha=0.9)
        for x in range(int(xmin), int(xmax) + 1):
            if x % 5 != 0:
                ax.plot([x, x], [ymin, ymin + 0.6], color="white", lw=0.8, alpha=0.6)
                ax.plot([x, x], [ymax - 0.6, ymax], color="white", lw=0.8, alpha=0.6)
        ax.axhline(0, color="white", lw=3, alpha=0.95)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.set_xlabel("Field Length (X Yards)", fontsize=12, fontweight="bold", labelpad=8)
        ax.set_ylabel("Field Width (Y Yards)", fontsize=12, fontweight="bold", labelpad=8)

    puka = comb.filter((pl.col("nfl_id") == 56042) & (pl.col("drill_name") == "COMEBACK_ROUTE_RIGHT") & (pl.col("entity_type") == "PLAYER")).sort("time")
    qj = comb.filter((pl.col("nfl_id") == 55885) & (pl.col("drill_name") == "COMEBACK_ROUTE_RIGHT") & (pl.col("entity_type") == "PLAYER")).sort("time")

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [1, 1]})
    
    # Subplot 1: Puka Nacua
    ax1 = axes[0]
    draw_nfl_field_section(ax1, xmin=22, xmax=44, ymin=-0.5, ymax=12)
    s_kmh_puka = puka["s"].to_numpy() * 3.29184
    sc1 = ax1.scatter(puka["x"], puka["y"], c=s_kmh_puka, cmap="plasma", s=65, zorder=4, edgecolor="black", lw=0.5)
    ax1.plot(puka["x"], puka["y"], color="white", lw=1.5, alpha=0.7, linestyle="--", zorder=3)
    ax1.annotate("START (Release)", xy=(puka["x"][0], puka["y"][0]), xytext=(puka["x"][0]-1.5, puka["y"][0]+2.0),
                 arrowprops=dict(arrowstyle="->", color="white", lw=1.2), color="white", fontweight="bold", fontsize=10)
    break_idx_puka = int(np.argmax(puka["x"].to_numpy()))
    ax1.annotate(f"BREAK POINT (18 yd stem)\nPeak Braking: -5.77 yd/s²\nSpeed: {s_kmh_puka[break_idx_puka]:.1f} km/h", 
                 xy=(float(puka["x"][break_idx_puka]), float(puka["y"][break_idx_puka])), 
                 xytext=(float(puka["x"][break_idx_puka])-7.5, float(puka["y"][break_idx_puka])-3.5),
                 arrowprops=dict(arrowstyle="->", color="cyan", lw=1.8), color="cyan", fontweight="bold", fontsize=10, 
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#1b263b", edgecolor="cyan", alpha=0.85))
    ax1.set_title("Puka Nacua (Pick 177, All-Pro) — Combine Comeback Route Kinematics", fontsize=13, fontweight="bold", pad=10)

    # Subplot 2: Quentin Johnston
    ax2 = axes[1]
    draw_nfl_field_section(ax2, xmin=22, xmax=44, ymin=-0.5, ymax=12)
    s_kmh_qj = qj["s"].to_numpy() * 3.29184
    sc2 = ax2.scatter(qj["x"], qj["y"], c=s_kmh_qj, cmap="plasma", s=65, zorder=4, edgecolor="black", lw=0.5)
    ax2.plot(qj["x"], qj["y"], color="white", lw=1.5, alpha=0.7, linestyle="--", zorder=3)
    ax2.annotate("START (Release)", xy=(float(qj["x"][0]), float(qj["y"][0])), xytext=(float(qj["x"][0])-1.5, float(qj["y"][0])+2.0),
                 arrowprops=dict(arrowstyle="->", color="white", lw=1.2), color="white", fontweight="bold", fontsize=10)
    break_idx_qj = int(np.argmax(qj["x"].to_numpy()))
    ax2.annotate(f"BREAK POINT (18 yd stem)\nPeak Braking: -5.23 yd/s²\nSpeed: {s_kmh_qj[break_idx_qj]:.1f} km/h", 
                 xy=(float(qj["x"][break_idx_qj]), float(qj["y"][break_idx_qj])), 
                 xytext=(float(qj["x"][break_idx_qj])-7.5, float(qj["y"][break_idx_qj])-3.5),
                 arrowprops=dict(arrowstyle="->", color="#ffbe0b", lw=1.8), color="#ffbe0b", fontweight="bold", fontsize=10,
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#1b263b", edgecolor="#ffbe0b", alpha=0.85))
    ax2.set_title("Quentin Johnston (Pick 21, 1st Round) — Combine Comeback Route Kinematics", fontsize=13, fontweight="bold", pad=10)

    cbar = fig.colorbar(sc1, ax=axes.ravel().tolist(), orientation="horizontal", fraction=0.046, pad=0.15)
    cbar.set_label("Instantaneous Movement Speed (km/h)", fontsize=11, fontweight="bold")
    plt.tight_layout()
    field_plot_path = os.path.join(BASE_DIR, "route_kinematics_field_plot.png")
    plt.savefig(field_plot_path, dpi=300)
    plt.close()
    print(f"Saved: {field_plot_path}")

    # -------------------------------------------------------------
    # 3. mass_vs_gamma_scatter.png
    # -------------------------------------------------------------
    print("Generating mass_vs_gamma_scatter.png...")
    dl_ids = players.filter(pl.col("nfl_position").is_in(["DE", "DT", "NT", "OLB"]))["nfl_id"].to_list()
    dl_drills = comb.filter((pl.col("nfl_id").is_in(dl_ids)) & (pl.col("entity_type") == "PLAYER"))
    dl_feat = dl_drills.group_by("nfl_id").agg([
        (pl.col("a") * 3.29184).quantile(0.90).alias("gamma_accel")
    ])
    df_p = dl_feat.join(comb_res, on="nfl_id").join(success, on="nfl_id").join(players, on="nfl_id").to_pandas()
    df_p = df_p.dropna(subset=["combine_weight", "gamma_accel"])

    mod = smf.ols("gamma_accel ~ combine_weight", data=df_p).fit()
    df_p["gamma_OE"] = mod.resid
    df_p["is_starter"] = (df_p["career_games_started"] >= 10).astype(int)

    plt.figure(figsize=(10, 6), facecolor="#0b0f19")
    ax = plt.gca()
    ax.set_facecolor("#161b26")
    starters = df_p[df_p["is_starter"] == 1]
    backups = df_p[df_p["is_starter"] == 0]

    plt.scatter(backups["combine_weight"], backups["gamma_accel"], color="#ef476f", alpha=0.6, s=55, label="Rotational / Fringe (<10 Starts)", edgecolors="none")
    plt.scatter(starters["combine_weight"], starters["gamma_accel"], color="#06d6a0", alpha=0.9, s=85, label="NFL Starters (>=10 Starts)", edgecolors="white", lw=1.2)

    w_line = np.linspace(df_p["combine_weight"].min() - 5, df_p["combine_weight"].max() + 5, 100)
    pred_gamma = mod.predict({"combine_weight": w_line})
    p_val = mod.pvalues.iloc[1]
    plt.plot(w_line, pred_gamma, color="white", linestyle="--", lw=2, label=f"Expected Gamma E[a|Mass] (p={p_val:.3f})")

    notable = ["Braden Fiske", "Laiatu Latu", "Gervon Dexter", "Dante Stills"]
    for _, r in df_p[df_p["display_name"].isin(notable)].iterrows():
        name = r["display_name"]
        oe = r["gamma_OE"]
        txt = f"{name}\n(+{oe:.2f} OE)"
        plt.annotate(txt, xy=(r["combine_weight"], r["gamma_accel"]), xytext=(r["combine_weight"] + 3, r["gamma_accel"] + 0.3),
                     arrowprops=dict(arrowstyle="->", color="#ffd166", lw=1.2), color="white", fontweight="bold", fontsize=9,
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#1b263b", edgecolor="#ffd166", alpha=0.85))

    plt.title("Newtonian Kinesiology: Mass vs. Instantaneous Acceleration (Gamma)", fontsize=14, fontweight="bold", color="white", pad=12)
    plt.xlabel("Combine Weight (lbs)", fontsize=12, fontweight="bold", color="white")
    plt.ylabel("90th Percentile Acceleration (Gamma, km/h/s)", fontsize=12, fontweight="bold", color="white")
    plt.tick_params(colors="white")
    plt.grid(True, alpha=0.15, color="white")
    plt.legend(facecolor="#1b263b", edgecolor="white", labelcolor="white", fontsize=10)

    plt.tight_layout()
    mass_gamma_path = os.path.join(BASE_DIR, "mass_vs_gamma_scatter.png")
    plt.savefig(mass_gamma_path, dpi=250)
    plt.close()
    print(f"Saved: {mass_gamma_path}")
    print("All static figures generated successfully!")

if __name__ == "__main__":
    make_all_plots()
