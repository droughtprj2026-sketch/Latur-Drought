# -*- coding: utf-8 -*-
"""
Senior Scientist Drought Analysis & Visualization Suite
-------------------------------------------------------
Generates comprehensive, publication-grade figures using Matplotlib, Seaborn, and GeoPandas:
1. 10-Year Cross-Index Pearson & Spearman Correlation Matrices
2. Annual Correlation Evolution Grid (2016 - 2026)
3. Multi-Variate Scatterplots & Regressions by Drought Severity Class
4. Spatial Village-Level Coupling Maps (Choropleth r(SPI, NDVI))
5. 11-Year Annual Drought Severity Spatial Atlas (2016 - 2026)
6. 10-Year Temporal Hovmöller Drought Evolution Heatmap
"""
import os
import sys
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
import geopandas as gpd

# Styling defaults for scientific publication
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#E0E0E0'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.6

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "processed" / "csv" / "village_with_baseline.csv"
GEOJSON_PATH = ROOT / "data" / "vector" / "latur_villages.geojson"
TEHSILS_PATH = ROOT / "data" / "vector" / "latur_tehsils.geojson"
OUT_DIR = ROOT / "output" / "figures" / "scientific_suite"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DROUGHT_PALETTE = {
    "None": "#43A047",      # Green (No Drought)
    "D0": "#FDD835",        # Yellow (Abnormally Dry / Mild)
    "D1": "#FB8C00",        # Orange (Moderate)
    "D2": "#E53935",        # Red (Severe)
    "D3": "#8E24AA",        # Purple (Extreme)
    "D4": "#4A148C",        # Dark Purple (Exceptional)
    "ND": "#BDBDBD"         # Grey (No Data)
}

INDEX_LABELS = {
    "Rain_mm": "Rainfall (mm)",
    "SPI1": "SPI-1",
    "SPI3": "SPI-3",
    "SPI6": "SPI-6",
    "SPI12": "SPI-12",
    "PCI": "Precip. Condition (PCI)",
    "NSMI": "Soil Moisture (NSMI)",
    "NDVI": "Vegetation (NDVI)",
    "VCI": "Veg. Condition (VCI)",
    "VHI": "Veg. Health (VHI)",
    "composite_drought_score": "Composite CDI"
}

def load_data():
    print("Loading village baseline dataset...")
    df = pd.read_csv(CSV_PATH)
    df["date"] = df["date"].astype(str)
    df["year"] = df["date"].str.slice(0, 4).astype(int)
    df["month"] = df["date"].str.slice(5, 7).astype(int)
    print(f"Loaded {len(df)} records across {df['village_idx'].nunique()} villages.")
    return df

def generate_10year_correlation_matrix(df):
    print("Generating Figure 1: 10-Year Cross-Index Correlation Matrix...")
    cols = ["Rain_mm", "SPI1", "SPI3", "SPI6", "SPI12", "PCI", "NSMI", "NDVI", "VCI", "VHI", "composite_drought_score"]
    valid_cols = [c for c in cols if c in df.columns]
    
    sub_df = df[valid_cols].rename(columns=INDEX_LABELS)
    corr = sub_df.corr(method="pearson")
    
    fig, ax = plt.subplots(figsize=(11, 9), dpi=300)
    mask = np.triu(np.ones_like(corr, dtype=bool))
    
    cmap = sns.diverging_palette(220, 20, as_cmap=True)
    
    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        vmax=1.0,
        vmin=-1.0,
        center=0,
        annot=True,
        fmt=".2f",
        square=True,
        linewidths=0.75,
        cbar_kws={"shrink": 0.8, "label": "Pearson Correlation Coefficient (r)"},
        annot_kws={"size": 10, "weight": "bold"},
        ax=ax
    )
    
    ax.set_title("10-Year Cross-Index Correlation Matrix (Latur District: 2016–2026)\nMeteorological, Hydrological, and Biophysical Interactions", fontsize=13, weight="bold", pad=15)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    plt.tight_layout()
    out_file = OUT_DIR / "fig1_10year_cross_index_correlation.png"
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Saved: {out_file}")

def generate_annual_correlation_grid(df):
    print("Generating Figure 2: Annual Correlation Evolution Grid (2016 - 2026)...")
    cols = ["Rain_mm", "SPI3", "NSMI", "NDVI", "VCI", "composite_drought_score"]
    labels = ["Rain", "SPI-3", "NSMI", "NDVI", "VCI", "CDI"]
    years = sorted(df["year"].unique())
    
    n_years = len(years)
    cols_grid = 4
    rows_grid = int(np.ceil(n_years / cols_grid))
    
    fig, axes = plt.subplots(rows_grid, cols_grid, figsize=(18, 4.2 * rows_grid), dpi=300)
    axes = axes.flatten()
    cmap = sns.diverging_palette(220, 20, as_cmap=True)
    
    for idx, year in enumerate(years):
        ax = axes[idx]
        ydf = df[df["year"] == year][cols]
        corr = ydf.corr()
        mask = np.triu(np.ones_like(corr, dtype=bool))
        
        sns.heatmap(
            corr,
            mask=mask,
            cmap=cmap,
            vmax=1.0,
            vmin=-1.0,
            center=0,
            annot=True,
            fmt=".2f",
            square=True,
            cbar=False,
            xticklabels=labels,
            yticklabels=labels,
            annot_kws={"size": 8},
            ax=ax
        )
        ax.set_title(f"Year {year}", fontsize=11, weight="bold")
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', rotation=0, labelsize=8)
        
    for j in range(idx + 1, len(axes)):
        fig.delaxes(axes[j])
        
    fig.suptitle("Inter-Index Correlation Dynamics Across Annual Cycles (2016–2026)\nCoupling of Meteorological, Radar Soil Moisture, and Vegetation Indices", fontsize=15, weight="bold", y=0.99)
    plt.tight_layout()
    out_file = OUT_DIR / "fig2_annual_correlation_evolution_grid.png"
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Saved: {out_file}")

def generate_multivariate_scatterplots(df):
    print("Generating Figure 3: Scientific Multivariate Scatterplots & Regressions...")
    fig, axes = plt.subplots(2, 2, figsize=(15, 13), dpi=300)
    sample_df = df.dropna(subset=["SPI3", "NDVI", "NSMI", "VCI", "composite_drought_score"]).sample(n=min(12000, len(df)), random_state=42)
    
    # 1. SPI-3 vs NDVI
    ax1 = axes[0, 0]
    sns.scatterplot(
        data=sample_df, x="SPI3", y="NDVI", hue="composite_drought_class",
        palette=DROUGHT_PALETTE, alpha=0.45, s=25, edgecolor=None, ax=ax1
    )
    sns.regplot(data=sample_df, x="SPI3", y="NDVI", scatter=False, ax=ax1, color="#1A237E", line_kws={"linewidth": 2, "linestyle": "--"})
    r_val = sample_df[["SPI3", "NDVI"]].corr().iloc[0, 1]
    ax1.set_title(f"Meteorological vs Vegetation Response\nSPI-3 vs NDVI (Pearson r = {r_val:.2f})", weight="bold", fontsize=11)
    ax1.set_xlabel("Standardized Precipitation Index (SPI-3)", weight="bold")
    ax1.set_ylabel("Normalized Difference Vegetation Index (NDVI)", weight="bold")
    ax1.grid(True)
    if ax1.get_legend():
        ax1.get_legend().remove()
    
    # 2. SPI-3 vs NSMI (Soil Moisture)
    ax2 = axes[0, 1]
    sns.scatterplot(
        data=sample_df, x="SPI3", y="NSMI", hue="composite_drought_class",
        palette=DROUGHT_PALETTE, alpha=0.45, s=25, edgecolor=None, ax=ax2
    )
    sns.regplot(data=sample_df, x="SPI3", y="NSMI", scatter=False, ax=ax2, color="#004D40", line_kws={"linewidth": 2, "linestyle": "--"})
    r_val2 = sample_df[["SPI3", "NSMI"]].corr().iloc[0, 1]
    ax2.set_title(f"Meteorological vs Soil Moisture Coupling\nSPI-3 vs NSMI (Pearson r = {r_val2:.2f})", weight="bold", fontsize=11)
    ax2.set_xlabel("Standardized Precipitation Index (SPI-3)", weight="bold")
    ax2.set_ylabel("Normalized Soil Moisture Index (NSMI)", weight="bold")
    ax2.grid(True)
    if ax2.get_legend():
        ax2.get_legend().remove()

    # 3. NSMI vs VCI
    ax3 = axes[1, 0]
    sns.scatterplot(
        data=sample_df, x="NSMI", y="VCI", hue="composite_drought_class",
        palette=DROUGHT_PALETTE, alpha=0.45, s=25, edgecolor=None, ax=ax3
    )
    sns.regplot(data=sample_df, x="NSMI", y="VCI", scatter=False, ax=ax3, color="#BF360C", line_kws={"linewidth": 2, "linestyle": "--"})
    r_val3 = sample_df[["NSMI", "VCI"]].corr().iloc[0, 1]
    ax3.set_title(f"Soil Moisture vs Vegetation Condition\nNSMI vs VCI (Pearson r = {r_val3:.2f})", weight="bold", fontsize=11)
    ax3.set_xlabel("Normalized Soil Moisture Index (NSMI)", weight="bold")
    ax3.set_ylabel("Vegetation Condition Index (VCI %)", weight="bold")
    ax3.grid(True)
    if ax3.get_legend():
        ax3.get_legend().remove()

    # 4. SPI-3 vs Composite CDI Score
    ax4 = axes[1, 1]
    sns.scatterplot(
        data=sample_df, x="SPI3", y="composite_drought_score", hue="composite_drought_class",
        palette=DROUGHT_PALETTE, alpha=0.55, s=25, edgecolor=None, ax=ax4
    )
    ax4.axhline(0.20, color="gray", linestyle=":", label="D0 Threshold (0.20)")
    ax4.axhline(0.35, color="orange", linestyle=":", label="D1 Threshold (0.35)")
    ax4.axhline(0.50, color="red", linestyle=":", label="D2 Threshold (0.50)")
    ax4.axhline(0.65, color="purple", linestyle=":", label="D3 Threshold (0.65)")
    r_val4 = sample_df[["SPI3", "composite_drought_score"]].corr().iloc[0, 1]
    ax4.set_title(f"Composite Drought Score vs Rainfall Anomaly\nSPI-3 vs CDI Score (Pearson r = {r_val4:.2f})", weight="bold", fontsize=11)
    ax4.set_xlabel("Standardized Precipitation Index (SPI-3)", weight="bold")
    ax4.set_ylabel("Composite Drought Index Score (0–1)", weight="bold")
    ax4.grid(True)
    ax4.legend(title="Drought Severity", loc="upper right", framealpha=0.9, fontsize=8)

    fig.suptitle("Multivariate Biophysical & Meteorological Relationships in Latur District\nRigorous Correlation and Nonlinear Drought Regime Boundaries", fontsize=14, weight="bold")
    plt.tight_layout()
    out_file = OUT_DIR / "fig3_multivariate_scatterplots_and_regressions.png"
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Saved: {out_file}")

def generate_spatial_correlation_map(df):
    print("Generating Figure 4: Spatial Village-Level Correlation Map...")
    if not GEOJSON_PATH.exists():
        print(f"Skipping spatial map: {GEOJSON_PATH} not found.")
        return
        
    gdf = gpd.read_file(GEOJSON_PATH)
    gdf["village_idx"] = gdf.index + 1
    
    # Calculate per-village Pearson r(SPI3, NDVI)
    village_corrs = []
    for v_idx, grp in df.groupby("village_idx"):
        valid = grp[["SPI3", "NDVI"]].dropna()
        if len(valid) > 12:
            r = valid["SPI3"].corr(valid["NDVI"])
        else:
            r = np.nan
        village_corrs.append({"village_idx": v_idx, "spi_ndvi_corr": r})
    
    corr_df = pd.DataFrame(village_corrs)
    merged_gdf = gdf.merge(corr_df, on="village_idx", how="left")
    
    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
    merged_gdf.plot(
        column="spi_ndvi_corr",
        cmap="Spectral",
        legend=True,
        edgecolor="black",
        linewidth=0.15,
        missing_kwds={"color": "lightgrey", "label": "Insufficient Data"},
        legend_kwds={"label": "Pearson Correlation (SPI-3 vs NDVI)", "orientation": "horizontal", "shrink": 0.65, "pad": 0.05},
        ax=ax
    )
    
    if TEHSILS_PATH.exists():
        tehsils_gdf = gpd.read_file(TEHSILS_PATH)
        tehsils_gdf.boundary.plot(ax=ax, color="#1A1A1A", linewidth=1.2, linestyle="-")
        for _, row in tehsils_gdf.iterrows():
            centroid = row.geometry.centroid
            t_name = row.get("TEHSIL") or row.get("name") or ""
            ax.text(centroid.x, centroid.y, str(t_name).upper(), fontsize=9, weight="bold", color="#111111",
                    ha="center", va="center", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.6))
            
    ax.set_title("Spatial Sensitivity of Vegetation to Meteorological Deficits (2016–2026)\nVillage-Level Pearson Correlation r(SPI-3, NDVI) Across Latur District", fontsize=13, weight="bold")
    ax.axis("off")
    plt.tight_layout()
    out_file = OUT_DIR / "fig4_spatial_village_correlation_map.png"
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Saved: {out_file}")

def generate_annual_drought_atlas(df):
    print("Generating Figure 5: 11-Year Annual Drought Severity Spatial Atlas...")
    if not GEOJSON_PATH.exists():
        print("Skipping atlas: GeoJSON not found.")
        return
        
    gdf = gpd.read_file(GEOJSON_PATH)
    gdf["village_idx"] = gdf.index + 1
    
    years = sorted(df["year"].unique())
    n_years = len(years)
    cols_grid = 4
    rows_grid = int(np.ceil(n_years / cols_grid))
    
    annual_means = df.groupby(["village_idx", "year"])["composite_drought_score"].mean().reset_index()
    
    fig, axes = plt.subplots(rows_grid, cols_grid, figsize=(18, 4.5 * rows_grid), dpi=300)
    axes = axes.flatten()
    
    cmap = LinearSegmentedColormap.from_list("cdi_scientific", ["#2E7D32", "#FFF176", "#FFA726", "#D32F2F", "#4A148C"])
    
    for idx, year in enumerate(years):
        ax = axes[idx]
        ydf = annual_means[annual_means["year"] == year]
        m = gdf.merge(ydf, on="village_idx", how="left")
        
        m.plot(
            column="composite_drought_score",
            cmap=cmap,
            vmin=0.0,
            vmax=0.6,
            edgecolor="none",
            missing_kwds={"color": "#E0E0E0"},
            ax=ax
        )
        if TEHSILS_PATH.exists():
            t_gdf = gpd.read_file(TEHSILS_PATH)
            t_gdf.boundary.plot(ax=ax, color="#424242", linewidth=0.6)
            
        mean_score = ydf["composite_drought_score"].mean()
        ax.set_title(f"Year {year} (Mean CDI: {mean_score:.2f})", fontsize=10, weight="bold")
        ax.axis("off")
        
    for j in range(idx + 1, len(axes)):
        fig.delaxes(axes[j])
        
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0.0, vmax=0.6))
    sm._A = []
    cbar = fig.colorbar(sm, ax=axes.tolist(), orientation='horizontal', fraction=0.03, pad=0.04, aspect=40)
    cbar.set_label("Annual Mean Composite Drought Index (CDI)", weight="bold", fontsize=11)
    
    fig.suptitle("Spatial Atlas of Annual Drought Severity Across 954 Villages (2016–2026)\nEvolution of Regional Drought Vulnerability & High-Stress Episodes", fontsize=15, weight="bold", y=0.99)
    plt.tight_layout()
    out_file = OUT_DIR / "fig5_annual_drought_severity_atlas.png"
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Saved: {out_file}")

def generate_temporal_hovmoller_heatmap(df):
    print("Generating Figure 6: 10-Year Temporal Hovmöller Drought Evolution Heatmap...")
    monthly_stats = df.groupby(["year", "month"])[["composite_drought_score", "SPI3", "Rain_mm", "NSMI"]].mean().reset_index()
    
    pivot_cdi = monthly_stats.pivot(index="month", columns="year", values="composite_drought_score")
    pivot_spi = monthly_stats.pivot(index="month", columns="year", values="SPI3")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 11), dpi=300, sharex=True)
    
    # CDI Heatmap
    cdi_cmap = LinearSegmentedColormap.from_list("cdi_map", ["#2E7D32", "#FFF176", "#FFA726", "#D32F2F", "#4A148C"])
    sns.heatmap(
        pivot_cdi,
        cmap=cdi_cmap,
        vmin=0.0,
        vmax=0.65,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"label": "District Mean CDI Score"},
        ax=ax1
    )
    ax1.set_title("A. Composite Drought Index (CDI) Severity: Month × Year Matrix", fontsize=12, weight="bold")
    ax1.set_ylabel("Calendar Month", weight="bold")
    ax1.set_yticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], rotation=0)
    
    # SPI-3 Heatmap
    spi_cmap = sns.diverging_palette(20, 220, as_cmap=True)
    sns.heatmap(
        pivot_spi,
        cmap=spi_cmap,
        center=0,
        vmin=-2.5,
        vmax=2.5,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"label": "District Mean SPI-3"},
        ax=ax2
    )
    ax2.set_title("B. Standardized Precipitation Index (SPI-3): Month × Year Matrix", fontsize=12, weight="bold")
    ax2.set_ylabel("Calendar Month", weight="bold")
    ax2.set_xlabel("Year (2016–2026)", weight="bold")
    ax2.set_yticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], rotation=0)
    
    fig.suptitle("10-Year Temporal Hovmöller Matrix of Drought Evolution (Latur District: 2016–2026)\nTracking Seasonal Onset, Peak Intensity, and Post-Monsoon Recovery", fontsize=14, weight="bold")
    plt.tight_layout()
    out_file = OUT_DIR / "fig6_temporal_hovmoller_drought_matrix.png"
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Saved: {out_file}")

def main():
    print("=" * 60)
    print("LATUR DROUGHT SCIENTIFIC VISUALIZATION SUITE")
    print("=" * 60)
    df = load_data()
    generate_10year_correlation_matrix(df)
    generate_annual_correlation_grid(df)
    generate_multivariate_scatterplots(df)
    generate_spatial_correlation_map(df)
    generate_annual_drought_atlas(df)
    generate_temporal_hovmoller_heatmap(df)
    print("=" * 60)
    print(f"ALL 6 HIGH-RESOLUTION SCIENTIFIC FIGURES GENERATED IN: {OUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
