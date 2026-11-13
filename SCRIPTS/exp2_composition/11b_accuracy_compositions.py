"""
Accuracy of the cube compositions by the ratio estimator of Stehman (2014).

The validation points were drawn on the concordance map of the three segmentation
classifications, so the strata differ from the classes of any evaluated map. Each point
is weighted by N_h / n_h of the stratum where it was drawn; the same points evaluate
every map. Outputs per experiment: overall, user's and producer's accuracy of all
classes with 95% CI (1.96 x SE), and two figures.

Stehman, S.V. (2014). Int. J. Remote Sens. 35(13), 4923-4939.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy.ndimage import minimum_filter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CONCORDANCE_RASTER = Path("maps/concordance_sampling_strata.tif")

NAME = "EXP"
POINTS_GPKG = Path("samples/validation_points_maps_EXP.gpkg")
OUTPUT = Path("results/stehman/EXP")
# {label: column of the points file}, in the order of the figures
MAPS = {"DB_B": "map_DB_B",
        "DB_B_IS": "map_DB_B_IS",
        "DB_B_S": "map_DB_B_S",
        "DB_FULL": "map_DB_FULL"}

# the points files have no stratum column: it is read from the concordance raster
COL_STRATUM = "Stratum"
COL_REF = "Revisor"

# concordance raster codes -> strata (99 = disagreement); FLO (13), NFLO (14) and
# nodata are outside the sampled population
STRATA_DICT = {
    1: "AGPE", 2: "AGUA", 3: "AL", 4: "DMC", 5: "DMF", 6: "PA",
    7: "PH", 8: "PSI", 9: "SE", 10: "URB", 11: "VSA", 12: "VSI",
    99: "DISCORD",
}

CLASSES = ["AGPE", "AGUA", "AL", "DMC", "DMF", "PA", "PH", "PSI", "SE", "URB", "VSA", "VSI"]
FOCUS_CLASS = "AGPE"

# N_h from the eroded area (True) or from the total area of each stratum (False)
USE_EROSION = False
BUFFER_PX = 5

DPI = 700
COLORS = {"Overall": "#2F4A66", "Producer's": "#2A7F75", "User's": "#B9771E"}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def compute_nh(a, erosion=True, buffer_px=5):
    nh = {}
    size = 2 * buffer_px + 1
    for code, label in STRATA_DICT.items():
        m = (a == code).astype(np.uint8)
        if not m.any():
            continue
        if erosion:
            m = minimum_filter(m, size=size, mode="constant", cval=0)
        nh[label] = int(m.sum(dtype=np.int64))
    return nh


def point_strata(gdf, src):
    g = gdf.to_crs(src.crs)
    vals = np.array([v[0] for v in src.sample([(p.x, p.y) for p in g.geometry])])
    return pd.Series([STRATA_DICT.get(int(v), f"OUT({int(v)})") for v in vals], index=gdf.index)


def ratio_estimator(y, x, s, nh):
    # R = Y / X, Y = sum_h N_h * mean_h(y), X = sum_h N_h * mean_h(x)
    # V(R) = (1 / X^2) * sum_h N_h^2 (1 - n_h / N_h) var_h(y - R x) / n_h
    Y = X = 0.0
    for h, Nh in nh.items():
        i = s == h
        if i.any() and Nh > 0:
            Y += Nh * y[i].mean()
            X += Nh * x[i].mean()
    if X == 0:
        return np.nan, np.nan
    R = Y / X
    V = 0.0
    for h, Nh in nh.items():
        i = s == h
        n_h = int(i.sum())
        if n_h < 2 or Nh == 0:
            continue
        d = y[i] - R * x[i]
        V += Nh ** 2 * (1 - n_h / Nh) * d.var(ddof=1) / n_h
    return R, np.sqrt(V) / X


def estimate_map(data, column, label, nh):
    # valid point: map and reference in one of the 12 classes. Points the map labels
    # FLO/NFLO leave the map's domain but still count in the stratum sample size.
    s = data[COL_STRATUM].astype(str).to_numpy()
    r = data[COL_REF].astype(str).to_numpy()
    m = data[column].astype(str).to_numpy()
    valid = np.isin(m, CLASSES) & np.isin(r, CLASSES)

    rows = []
    oa, se = ratio_estimator((valid & (m == r)).astype(float), valid.astype(float), s, nh)
    rows.append(dict(Map=label, Metric="Overall", Class="Overall", Value=oa, SE=se))
    for k in CLASSES:
        hit = (valid & (m == k) & (r == k)).astype(float)
        ua, se_ua = ratio_estimator(hit, (valid & (m == k)).astype(float), s, nh)
        pa, se_pa = ratio_estimator(hit, (valid & (r == k)).astype(float), s, nh)
        rows.append(dict(Map=label, Metric="Producer's", Class=k, Value=pa, SE=se_pa))
        rows.append(dict(Map=label, Metric="User's", Class=k, Value=ua, SE=se_ua))

    tab = pd.DataFrame(rows)
    tab["Value"] *= 100
    tab["SE"] *= 100
    tab["CI95"] = 1.96 * tab["SE"]
    tab["n_valid"] = int(valid.sum())
    tab["n_excluded"] = int((~valid).sum())
    return tab


def _labels(ax, bars, values, errors, fmt, size):
    for b, v, e in zip(bars, values, errors):
        if np.isnan(v):
            continue
        top = min(100, v + (0 if np.isnan(e) else e))
        ax.text(b.get_x() + b.get_width() / 2, top + 1.5, fmt.format(v),
                ha="center", va="bottom", fontsize=size, fontweight="bold", color="#222222")


def plot_summary(tab, order, path):
    series = [("Overall", "Overall", "Overall"),
              (f"Producer's {FOCUS_CLASS}", "Producer's", FOCUS_CLASS),
              (f"User's {FOCUS_CLASS}", "User's", FOCUS_CLASS)]
    x = np.arange(len(order))
    w = 0.26
    fig, ax = plt.subplots(figsize=(1.6 + 1.5 * len(order), 4.6))
    for j, (name, metric, cl) in enumerate(series):
        d = tab[(tab.Metric == metric) & (tab.Class == cl)].set_index("Map").reindex(order)
        v, e = d["Value"].to_numpy(), d["CI95"].to_numpy()
        lo = np.clip(v - e, 0, 100)
        hi = np.clip(v + e, 0, 100)
        bars = ax.bar(x + (j - 1) * w, v, w * 0.95, color=COLORS[metric], edgecolor="black",
                      linewidth=0.4, label=name, zorder=3)
        ax.errorbar(x + (j - 1) * w, v, yerr=[v - lo, hi - v], fmt="none", ecolor="#333333",
                    elinewidth=0.8, capsize=3, zorder=4)
        _labels(ax, bars, v, e, "{:.1f}", 8.5)
    ax.set_xticks(x, order, fontweight="bold")
    ax.set_ylim(0, 108)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Accuracy (%)")
    ax.grid(axis="y", color="#DDDDDD", zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    fig.text(0.99, -0.01, "Error bars: 95% confidence interval (Stehman, 2014)",
             ha="right", va="top", fontsize=7.5, color="#666666")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def plot_classes(tab, order, path):
    x = np.arange(len(CLASSES))
    w = 0.38
    fig, axs = plt.subplots(len(order), 1, figsize=(8.6, 1.2 + 2.3 * len(order)), sharex=True)
    axs = np.atleast_1d(axs)
    for ax, map_name in zip(axs, order):
        dm = tab[tab.Map == map_name]
        oa = dm[dm.Metric == "Overall"].iloc[0]
        for j, metric in enumerate(["Producer's", "User's"]):
            d = dm[dm.Metric == metric].set_index("Class").reindex(CLASSES)
            v, e = d["Value"].to_numpy(), d["CI95"].to_numpy()
            lo = np.clip(v - e, 0, 100)
            hi = np.clip(v + e, 0, 100)
            bars = ax.bar(x + (j - 0.5) * w, v, w * 0.95, color=COLORS[metric], edgecolor="black",
                          linewidth=0.3, label=metric, zorder=3)
            ax.errorbar(x + (j - 0.5) * w, v, yerr=[v - lo, hi - v], fmt="none", ecolor="#444444",
                        elinewidth=0.6, capsize=2, zorder=4)
            _labels(ax, bars, v, e, "{:.0f}", 6.5)
        ax.set_title(f"{map_name}  |  Overall = {oa.Value:.1f}% (±{oa.CI95:.1f})",
                     loc="left", fontsize=10, fontweight="bold")
        ax.set_ylim(0, 115)
        ax.set_yticks(range(0, 101, 25))
        ax.set_ylabel("Accuracy (%)")
        ax.grid(axis="y", color="#DDDDDD", zorder=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axs[-1].set_xticks(x, CLASSES)
    axs[0].legend(ncol=2, frameon=False, loc="lower right", bbox_to_anchor=(1.0, 1.02))
    fig.text(0.99, -0.005, "Error bars: 95% confidence interval (Stehman, 2014)",
             ha="right", va="top", fontsize=7.5, color="#666666")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    if not CONCORDANCE_RASTER.exists():
        raise FileNotFoundError(f"Concordance raster not found: {CONCORDANCE_RASTER}")

    src = rasterio.open(CONCORDANCE_RASTER)
    nh = compute_nh(src.read(1), erosion=USE_EROSION, buffer_px=BUFFER_PX)
    print(pd.Series(nh, name="N_h").to_string())

    OUTPUT.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(POINTS_GPKG)
    gdf = gdf[gdf.geometry.notna()]
    gdf[COL_STRATUM] = point_strata(gdf, src)
    outside = gdf[COL_STRATUM].str.startswith("OUT")
    if outside.any():
        print(f"Warning: {int(outside.sum())} points outside the sampled strata (FLO/NFLO/nodata), removed:")
        print(gdf.loc[outside, COL_STRATUM].value_counts().to_string())
        gdf = gdf[~outside]
    data = pd.DataFrame(gdf.drop(columns="geometry"))

    missing = set(MAPS.values()) | {COL_STRATUM, COL_REF}
    missing -= set(data.columns)
    if missing:
        raise KeyError(f"Missing columns in the gpkg: {sorted(missing)}")

    zeroed = sorted(h for h in set(data[COL_STRATUM].astype(str)) if nh.get(h, 1) == 0)
    if zeroed:
        raise ValueError(f"Strata with points but N_h = 0 after erosion: {zeroed}. "
                         "Check BUFFER_PX or set USE_EROSION = False.")

    no_nh = set(data[COL_STRATUM].astype(str)) - set(nh)
    if no_nh:
        raise KeyError(f"Strata of the points without N_h: {sorted(no_nh)}. "
                       "Check STRATA_DICT and the concordance raster.")

    print("Points per stratum:")
    print(data[COL_STRATUM].value_counts().to_string())

    tab = pd.concat([estimate_map(data, col, label, nh) for label, col in MAPS.items()],
                    ignore_index=True)

    print("\nValid / excluded points (FLO, NFLO or no reference) per map:")
    print(tab.drop_duplicates("Map")[["Map", "n_valid", "n_excluded"]].to_string(index=False))

    tab.round({"Value": 2, "SE": 2, "CI95": 2}).to_csv(
        OUTPUT / f"Stehman_accuracy_{NAME}.csv", sep=";", decimal=",", index=False)

    order = list(MAPS.keys())
    plot_summary(tab, order, OUTPUT / f"Accuracy_overall_{FOCUS_CLASS}_{NAME}.png")
    plot_classes(tab, order, OUTPUT / f"Accuracy_classes_{NAME}.png")

    summary = tab[(tab.Metric == "Overall") | (tab.Class == FOCUS_CLASS)]
    print("\n" + summary[["Map", "Metric", "Class", "Value", "CI95"]].round(2).to_string(index=False))

    src.close()


if __name__ == "__main__":
    main()
