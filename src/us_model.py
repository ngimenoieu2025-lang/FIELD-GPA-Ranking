"""OLS equivalent of ministry.field_effects, using NumPy/SciPy.

Same design: mean ~ C(field, Sum) + C(univ) + C(year).
This implementation also checks identification explicitly.
"""
import numpy as np
import pandas as pd
from scipy.stats import f as f_distribution


def field_effects(df):
    fields = sorted(df.field.unique())
    if len(fields) < 2:
        raise ValueError('At least two fields are required')
    dummies = [pd.get_dummies(df[c].astype(str), drop_first=True, dtype=float).to_numpy()
               for c in ['univ', 'year']]
    base = np.column_stack([np.ones(len(df)), *dummies])
    contrast = np.column_stack([(df.field.eq(f).astype(float) - df.field.eq(fields[-1]).astype(float)).to_numpy()
                                for f in fields[:-1]])
    x = np.column_stack([base, contrast])
    y = df['mean'].to_numpy(float)
    coef, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if rank != x.shape[1] or len(y) <= rank:
        raise ValueError('Fixed-effects design is not identified or has no residual degrees of freedom')
    rss = float(np.sum((y - x @ coef)**2))
    residual_df = len(y) - rank
    cov = np.linalg.inv(x.T @ x) * (rss / residual_df)
    k = len(fields)-1
    est, cov = coef[-k:], cov[-k:, -k:]
    effect = np.r_[est, -est.sum()]
    se = np.sqrt(np.maximum(0., np.r_[np.diag(cov), cov.sum()]))
    out = pd.DataFrame({'effect': effect, 'se': se}, index=fields).sort_values('effect')
    base_coef = np.linalg.lstsq(base, y, rcond=None)[0]
    base_rss = float(np.sum((y-base@base_coef)**2))
    tss = float(np.sum((y-y.mean())**2))
    f_stat = max(0., (base_rss-rss)/k)/(rss/residual_df) if rss > 0 else float('inf')
    stats = {'r2_univ_year': 1-base_rss/tss, 'r2_with_field': 1-rss/tss,
             'f_test_field': {'F': f_stat, 'p': float(f_distribution.sf(f_stat, k, residual_df)), 'df': float(k)},
             'n_obs': len(df), 'n_univ': int(df.univ.nunique()), 'n_fields': len(fields)}
    return out, stats
