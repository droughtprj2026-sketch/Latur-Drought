# -*- coding: utf-8 -*-
"""Statistical primitives used by the figure suite.

Deliberately small and inspectable: Pearson / Spearman with p-values, OLS via
``scipy.stats.linregress``, Fisher-z confidence intervals, Mann-Kendall trend
tests and Sen's slope. No black-box models -- the composite itself is a
transparent weighted index (see config/composite.yaml).
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy import stats


# --------------------------------------------------------------------------
# Bivariate statistics
# --------------------------------------------------------------------------
def _clean(x, y) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def pearson(x, y) -> tuple[float, float, int]:
    x, y = _clean(x, y)
    if x.size < 3:
        return np.nan, np.nan, int(x.size)
    r, p = stats.pearsonr(x, y)
    return float(r), float(p), int(x.size)


def spearman(x, y) -> tuple[float, float, int]:
    x, y = _clean(x, y)
    if x.size < 3:
        return np.nan, np.nan, int(x.size)
    r, p = stats.spearmanr(x, y)
    return float(r), float(p), int(x.size)


def fisher_ci(r: float, n: int, level: float = 0.95) -> tuple[float, float]:
    """Confidence interval for a Pearson r via the Fisher z transform."""
    if not np.isfinite(r) or n < 4 or abs(r) >= 1.0:
        return (np.nan, np.nan)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    crit = stats.norm.ppf(0.5 + level / 2.0)
    return (float(np.tanh(z - crit * se)), float(np.tanh(z + crit * se)))


def ols(x, y) -> dict:
    """Ordinary least squares with the diagnostics a reviewer asks for."""
    x, y = _clean(x, y)
    n = int(x.size)
    if n < 3 or np.ptp(x) == 0:
        return {"n": n, "slope": np.nan, "intercept": np.nan, "r": np.nan, "r2": np.nan,
                "p": np.nan, "stderr": np.nan}
    fit = stats.linregress(x, y)
    return {
        "n": n,
        "slope": float(fit.slope),
        "intercept": float(fit.intercept),
        "r": float(fit.rvalue),
        "r2": float(fit.rvalue ** 2),
        "p": float(fit.pvalue),
        "stderr": float(fit.stderr),
    }


def regression_table(df: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for xcol, ycol in pairs:
        if xcol not in df.columns or ycol not in df.columns:
            continue
        res = ols(df[xcol], df[ycol])
        r_s, p_s, n_s = spearman(df[xcol], df[ycol])
        lo, hi = fisher_ci(res["r"], res["n"])
        rows.append(
            {
                "predictor": C_LABEL(xcol),
                "response": C_LABEL(ycol),
                "n": res["n"],
                "pearson_r": round(res["r"], 4),
                "r_ci_low": round(lo, 4),
                "r_ci_high": round(hi, 4),
                "r2": round(res["r2"], 4),
                "slope": round(res["slope"], 6),
                "intercept": round(res["intercept"], 6),
                "stderr_slope": round(res["stderr"], 6),
                "p_value": res["p"],
                "spearman_rho": round(r_s, 4),
                "spearman_p": p_s,
            }
        )
    return pd.DataFrame(rows)


def C_LABEL(column: str) -> str:
    from . import config as C

    return C.COL[column].label if column in C.COL else column


# --------------------------------------------------------------------------
# Correlation matrices
# --------------------------------------------------------------------------
def corr_matrix(df: pd.DataFrame, columns: list[str], method: str = "pearson") -> pd.DataFrame:
    cols = [c for c in columns if c in df.columns]
    return df[cols].corr(method=method, min_periods=3)


def corr_pvalues(df: pd.DataFrame, columns: list[str], method: str = "pearson") -> pd.DataFrame:
    cols = [c for c in columns if c in df.columns]
    out = pd.DataFrame(np.nan, index=cols, columns=cols, dtype=float)
    for a, b in itertools.combinations(cols, 2):
        _, p, n = (pearson if method == "pearson" else spearman)(df[a], df[b])
        out.loc[a, b] = p
        out.loc[b, a] = p
    for c in cols:
        out.loc[c, c] = 0.0
    return out


def pair_correlations(df: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for a, b in pairs:
        if a not in df.columns or b not in df.columns:
            continue
        r, p, n = pearson(df[a], df[b])
        rows.append({"a": a, "b": b, "r": r, "p": p, "n": n})
    return pd.DataFrame(rows)


def paired_correlation_by(df: pd.DataFrame, group: str, a: str, b: str, min_n: int = 12) -> pd.Series:
    def _one(sub):
        r, _, n = pearson(sub[a], sub[b])
        return r if n >= min_n else np.nan

    return df.groupby(group)[[a, b]].apply(_one)


def stars(p: float) -> str:
    if not np.isfinite(p):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."


# --------------------------------------------------------------------------
# Trend tests
# --------------------------------------------------------------------------
def mann_kendall(values) -> dict:
    """Non-parametric monotonic trend test (Mann-Kendall S statistic)."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = int(x.size)
    if n < 3:
        return {"n": n, "s": np.nan, "tau": np.nan, "z": np.nan, "p": np.nan, "trend": "insufficient"}

    s = 0.0
    for i in range(n - 1):
        s += float(np.sign(x[i + 1:] - x[i]).sum())

    var = n * (n - 1) * (2 * n + 5) / 18.0
    if s > 0:
        z = (s - 1) / np.sqrt(var)
    elif s < 0:
        z = (s + 1) / np.sqrt(var)
    else:
        z = 0.0
    p = float(2 * (1 - stats.norm.cdf(abs(z))))
    tau = s / (0.5 * n * (n - 1))

    if p < 0.05 and s > 0:
        trend = "increasing"
    elif p < 0.05 and s < 0:
        trend = "decreasing"
    else:
        trend = "no trend"
    return {"n": n, "s": s, "tau": float(tau), "z": float(z), "p": p, "trend": trend}


def sens_slope(values, index=None) -> dict:
    """Sen's slope (median pairwise slope) with its 95% confidence interval."""
    y = np.asarray(values, dtype=float)
    if index is None:
        index = np.arange(y.size, dtype=float)
    x = np.asarray(index, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if x.size < 3:
        return {"n": int(x.size), "slope": np.nan, "intercept": np.nan,
                "lo": np.nan, "hi": np.nan}
    slope, intercept, lo, hi = stats.theilslopes(y, x, alpha=0.95)
    return {"n": int(x.size), "slope": float(slope), "intercept": float(intercept),
            "lo": float(lo), "hi": float(hi)}


def trend_table(series_by_year: pd.Series, label: str) -> dict:
    y = series_by_year.dropna()
    mk = mann_kendall(y.to_numpy())
    ss = sens_slope(y.to_numpy(), index=y.index.to_numpy())
    return {
        "series": label,
        "n_years": int(y.size),
        "first_year": int(y.index.min()) if y.size else None,
        "last_year": int(y.index.max()) if y.size else None,
        "mean": round(float(y.mean()), 4) if y.size else np.nan,
        "sens_slope_per_year": round(ss["slope"], 6),
        "sens_slope_lo": round(ss["lo"], 6),
        "sens_slope_hi": round(ss["hi"], 6),
        "mk_tau": round(mk["tau"], 4),
        "mk_p": mk["p"],
        "trend": mk["trend"],
    }


# --------------------------------------------------------------------------
# Hypothesis tests
# --------------------------------------------------------------------------
def kruskal_by(df: pd.DataFrame, value: str, group: str) -> dict:
    groups = [g[value].dropna().to_numpy() for _, g in df.groupby(group) if g[value].notna().sum() >= 3]
    if len(groups) < 2:
        return {"test": "Kruskal-Wallis", "h": np.nan, "p": np.nan, "groups": len(groups)}
    h, p = stats.kruskal(*groups)
    return {"test": "Kruskal-Wallis", "h": float(h), "p": float(p), "groups": len(groups)}


def normality(series) -> dict:
    x = pd.Series(series).dropna().to_numpy()
    if x.size < 8:
        return {"test": "Shapiro-Wilk", "w": np.nan, "p": np.nan, "n": int(x.size)}
    sample = x if x.size <= 5000 else np.random.default_rng(0).choice(x, 5000, replace=False)
    w, p = stats.shapiro(sample)
    return {"test": "Shapiro-Wilk", "w": float(w), "p": float(p), "n": int(x.size)}


def lag_correlation(df: pd.DataFrame, driver: str, response: str,
                    max_lag: int = 6) -> pd.DataFrame:
    """Pooled lagged correlation across all villages.

    ``lag = k`` pairs the driver at month *t* with the response at month
    *t + k*, i.e. "how many months does the vegetation take to answer rainfall".
    """
    from . import data as D

    a = D.pivot_period_village(df, driver)
    b = D.pivot_period_village(df, response)
    idx = a.index.union(b.index).sort_values()
    a = a.reindex(idx)
    b = b.reindex(idx)

    a_np = a.to_numpy(dtype=float)
    b_np = b.to_numpy(dtype=float)

    rows = []
    for lag in range(0, max_lag + 1):
        if lag == 0:
            av, bv = a_np, b_np
        else:
            av, bv = a_np[:-lag], b_np[lag:]
        r, p, n = pearson(av.ravel(), bv.ravel())
        rows.append({"driver": driver, "response": response, "lag_months": lag,
                     "r": r, "p": p, "n": n})
    return pd.DataFrame(rows)
