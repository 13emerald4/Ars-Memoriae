# Beyond the Stopwatch: Evaluating NFL Prospects via Continuous Speed Densities, Newtonian Mechanics, and Gamma-Over-Expected

[![NFL Big Data Bowl 2027](https://img.shields.io/badge/NFL%20Big%20Data%20Bowl-2027-013369.svg)](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **Submission for the NFL Big Data Bowl 2027 (Kaggle Analytics Track)**  
> **Author:** Michael Polley  
> **Theme:** Linking 10 Hz Combine Sensor Tracking to Regular-Season NFL Game Performance

---

## 🏈 Executive Summary

Every draft season, NFL front offices spend millions in draft capital on **"Workout Warriors"**—athletes who run blazing 4.38-second 40-yard dashes in shorts, only to struggle creating a single yard of separation on Sundays.

A stopwatch records only one scalar number: total elapsed time ($T = \int \frac{dx}{v}$). It cannot observe how momentum is absorbed, whether hips decouple, or how rapidly speed decays in a cut.

This project bridges **high-frequency (10 Hz) Combine tracking data** with **regular-season NFL game performance** through a synthesis of **continuous speed distributions (PDF/CDF)**, **classical Newtonian mechanics ($F = ma$)**, and **frequentist econometrics (OLS, Logit, Welch's t-tests)**.

### Key Discoveries:
1. **The 40-Yard Dash Fails ($p = 0.343$):** In multivariable regression across 106 Combine WRs, official 40-yard dash times explain **zero statistically significant variance** in regular-season career snaps.
2. **In-Cut Velocity Preservation ($s_{\text{cut}}$) Dominates ($p = 0.002$):** Every $+1.0\text{ km/h}$ maintained through the apex of a route cut yields **$+132$ additional career regular-season snaps** and increases the odds of becoming an established NFL starter by **$+77\%$** ($p = 0.010, \text{OR} = 1.77$).
3. **Defensive Back Break Velocity ($p = 0.016$):** In 45-degree transition drills, 90th percentile break speed directly predicts defensive snaps ($\beta = +191.84, p = 0.016$), while 40-yard dash remains insignificant ($p = 0.471$).
4. **The Core Working Band (10–26 km/h):** Over 95% of in-game NFL movement occurs below $26\text{ km/h}$. All-Pros like Puka Nacua spend **63.5%** of drill time operating in this band, whereas raw track athletes skew toward an unutilized $>30\text{ km/h}$ tail.
5. **Gamma-Over-Expected ($\gamma_{\text{OE}}$) in Trench Play ($p = 0.042$):** For pass rushers and offensive linemen, acceleration residualized against body mass ($\gamma_{\text{OE}}$) increases DL starter odds by **$+85\%$** ($\text{OR} = 1.85$) and significantly predicts offensive snaps for linemen ($\beta = +154.98, p = 0.026$).

---

## 📊 Visualizations & Artifacts

| Artifact | Type | Description |
| :--- | :--- | :--- |
| **[`report_assigned.pdf`](./report_assigned.pdf)** | Formal Paper | 4-page research report formatted to formal LaTeX assignment style guidelines. |
| **[`REPORT.md`](./REPORT.md) / [`REPORT.html`](./REPORT.html)** | Submission | Competition research submission report (< 2,000 words, MathJax, embedded figures). |
| **[`presentation.tex`](./presentation.tex) / [`presentation.pdf`](./presentation.pdf)** | Beamer Deck | 10-slide presentation deck formatted for NFL front offices and competition judges. |
| **[`wr_speed_pdf_cdf.png`](./wr_speed_pdf_cdf.png)** | Static PNG | Speed Probability Density Function (PDF) and Cumulative Distribution Function (CDF) comparing All-Pros vs. 1st-Round sprinters. |
| **[`route_kinematics_field_plot.png`](./route_kinematics_field_plot.png)** | Static PNG | High-resolution publication diagram of Puka Nacua vs. Quentin Johnston executing the Combine Comeback drill on a regulation NFL turf slice. |
| **[`mass_vs_gamma_scatter.png`](./mass_vs_gamma_scatter.png)** | Static PNG | Mass vs. acceleration scatter plot establishing Newtonian Gamma-Over-Expected ($\gamma_{\text{OE}}$). |
| **[`tier_comparison_pdf_cdf.html`](./tier_comparison_pdf_cdf.html)** | Interactive HTML | Interactive cohort density analysis: Top Performers ($N=16$) vs. Average ($N=38$) vs. Fringe ($N=52$). |
| **[`route_playback_interactive.html`](./route_playback_interactive.html)** | Interactive HTML | 10 Hz frame-by-frame field playback with interactive scrubbing slider and live speed tags. |

---

## 🔬 Mathematical & Physical Methodology

### 1. Derivatives of Motion (Delta, Gamma, Jerk)
$$\mathbf{r}(t) = (x, y), \quad \mathbf{v}(t) = \frac{d\mathbf{r}}{dt} \ (\text{Delta}), \quad \mathbf{a}(t) = \frac{d\mathbf{v}}{dt} \ (\text{Gamma}), \quad \mathbf{j}(t) = \frac{d\mathbf{a}}{dt} \ (\text{Jerk})$$

### 2. Newtonian Ground Reaction Force & Inertia
$$\mathbf{F}_{\text{net}} = m \cdot \mathbf{a}, \quad \mathbf{p} = m \cdot \mathbf{v}, \quad P = \mathbf{F} \cdot \mathbf{v}$$
Because heavier athletes face greater inertia ($m$), we isolate specific explosive capacity by estimating **Gamma-Over-Expected ($\gamma_{\text{OE}}$)**:
$$\gamma_{\text{OE}} = \gamma_{\text{observed}} - \mathbb{E}[\gamma \mid \text{Mass}]$$

### 3. Frequentist Statistical Specifications
* **Career Playing Time Model (OLS):**
  $$\text{Snaps}_i = \beta_0 + \beta_1 (s_{\text{cut}, i}) + \beta_2 (\text{Forty}_i) + \epsilon_i$$
  *Result:* $\beta_1 = +132.09$ ($t = 3.125, p = 0.002$), $\beta_2 = -642.09$ ($t = -0.954, p = 0.343$).
* **Starter Probability Model (Logit):**
  $$\ln\left(\frac{P_i}{1 - P_i}\right) = \alpha + \beta_1 (s_{\text{cut}, i}) + \beta_2 (\text{Forty}_i)$$
  *Result:* $\beta_1 = +0.569$ ($z = 2.575, p = 0.010, \text{Odds Ratio} = 1.77$).

---

## 🛠️ Repository Structure

```text
nfl-bdb-2027/
├── README.md                           # Project thesis and empirical findings
├── presentation.tex                    # LaTeX Beamer 10-slide presentation deck
├── route_kinematics_field_plot.png     # Static figure: Regulation NFL field kinematics
├── wr_speed_pdf_cdf.png                # Static figure: Speed PDF & CDF comparisons
├── tier_comparison_pdf_cdf.html        # Interactive: Full cohort performance tiers
├── speed_pdf_cdf_interactive.html      # Interactive: Speed density exploration
├── route_playback_interactive.html     # Interactive: 10 Hz animated tracking playback
├── scripts/
│   ├── extract_features.py             # Feature extraction from 10 Hz tracking
│   ├── run_regressions.py              # Frequentist OLS & Logit models
│   ├── make_field_plot.py              # Matplotlib regulation field generator
│   └── make_interactive_playback.py    # Plotly animation builder
└── requirements.txt                    # Python environment specifications
```

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.11+
* [Kaggle CLI](https://github.com/Kaggle/kaggle-cli) (authenticated)

### 2. Installation
```bash
git clone https://github.com/your-username/nfl-bdb-2027.git
cd nfl-bdb-2027
pip install -r requirements.txt
```

### 3. Data Download
```bash
kaggle competitions download -c nfl-big-data-bowl-2027 -p data/
unzip data/nfl-big-data-bowl-2027.zip -d data/
```

### 4. Run Analysis & View Interactive Visuals
```bash
python scripts/run_regressions.py
# Open any interactive visual in your browser:
start route_playback_interactive.html
```

---

## 📋 Citation
```bibtex
@article{polley2027beyondstopwatch,
  title={Beyond the Stopwatch: Evaluating NFL Prospects via Continuous Speed Densities, Newtonian Mechanics, and Gamma-Over-Expected},
  author={Polley, Michael},
  journal={NFL Big Data Bowl 2027},
  year={2026}
}
```
