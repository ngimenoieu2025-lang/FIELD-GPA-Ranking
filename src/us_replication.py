"""Replicate Spanish field effects in the 33-institution Jeong et al. data.

Run from any directory: python src/us_replication.py
Raw data stay local; all exclusions and mapping decisions are exported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
from us_model import field_effects
ROOT = Path(__file__).resolve().parents[1]
from us_mapping import SPANISH_TO_AREA, build_mapping, normalize

POINTS = {'A+': 4.3, 'A': 4., 'A-': 3.67, 'B+': 3.33, 'B': 3., 'B-': 2.67,
          'C+': 2.33, 'C': 2., 'C-': 1.67, 'D+': 1.33, 'D': 1., 'D-': .67, 'F': 0.}


def section_gpa(df, a_plus=4.3):
    """Mean over numeric letter grades; percentages need not sum to 100.

    Blank grade categories are zero (the source uses blanks for unused grades).
    Pass, Fail (pass/fail scheme), W and Other are not numeric grades. F IS zero.
    Invalid/negative/>100 percentages and totals >101 are rejected. Renormalize
    the numeric-grade mass, so withdrawing students are not assigned zero GPA.
    """
    raw = df.reindex(columns=list(POINTS))
    grades = raw.apply(pd.to_numeric, errors='coerce')
    invalid_text = (raw.notna() & grades.isna()).any(axis=1)
    grades = grades.fillna(0.)
    mass = grades.sum(axis=1)
    invalid = invalid_text | (grades.lt(0) | grades.gt(100)).any(axis=1) | mass.gt(101)
    points = pd.Series({**POINTS, 'A+': a_plus})
    gpa = grades.mul(points).sum(axis=1).div(mass.where(mass.gt(0)))
    return gpa.mask(invalid), mass.mask(invalid)


def resolve_department_codes(df, mapping):
    """Fill absent codes only from an unambiguous exact name in this university."""
    codes = df.Department_Code.fillna('').map(normalize)
    names = mapping.department_name.map(lambda x: normalize(x).casefold())
    unique = ~names.duplicated(keep=False)
    lookup = dict(zip(names[unique], mapping.loc[unique, 'department_code']))
    source_names = df.Department_Name.fillna('').map(lambda x: normalize(x).casefold())
    missing = codes.eq('')
    codes.loc[missing] = source_names.loc[missing].map(lookup).fillna('')
    return codes


def load_sections(raw, mapping):
    files = sorted(raw.rglob('*.csv'))
    if len(files) != 33 or len({p.stem for p in files}) != 33:
        raise ValueError(f'Expected 33 uniquely named university CSVs; found {len(files)}')
    sections, audits, manifest = [], [], []
    for path in files:
        df = pd.read_csv(path, low_memory=False)
        required = {'Year', 'Department_Code', 'Enrollment', 'Department_Name', *POINTS}
        if not required.issubset(df.columns):
            raise ValueError(f'{path.name}: missing {required - set(df.columns)}')
        n_raw = len(df)
        df = df.drop_duplicates().copy()
        df['univ'] = path.stem
        df['source_row'] = df.index + 2
        m = mapping[mapping.univ.eq(path.stem)].drop(columns='univ')
        df['department_code'] = resolve_department_codes(df, m)
        df['gpa'], df['numeric_grade_percent'] = section_gpa(df)
        df['gpa_a4'], _ = section_gpa(df, a_plus=4.)
        df['enrollment'] = pd.to_numeric(df.Enrollment, errors='coerce')
        df['year'] = pd.to_numeric(df.Year, errors='coerce')
        df.loc[~df.year.between(1900, 2100) | df.year.mod(1).ne(0), 'year'] = np.nan
        df = df.merge(m, on='department_code', how='left', validate='many_to_one')
        df['field'] = df.field.fillna('')
        df['valid_gpa'] = df.gpa.notna() & df.year.notna()
        df['mapped'] = df.field.ne('')
        df['valid_weight'] = np.isfinite(df.enrollment) & df.enrollment.gt(0)
        usable = df.valid_gpa & df.mapped
        audits.append({'univ': path.stem, 'raw_rows': n_raw, 'exact_duplicates_removed': n_raw-len(df),
                       'rows_after_dedup': len(df), 'invalid_gpa_or_year': int((~df.valid_gpa).sum()),
                       'unmapped_rows': int((~df.mapped).sum()),
                       'usable_unweighted': int(usable.sum()),
                       'usable_weighted': int((usable & df.valid_weight).sum()),
                       'mapped_share_of_valid_rows': float(df.loc[df.valid_gpa, 'mapped'].mean())})
        sections.append(df[['univ', 'source_row', 'department_code', 'year', 'field', 'gpa', 'gpa_a4',
                            'numeric_grade_percent', 'enrollment', 'valid_gpa', 'mapped', 'valid_weight']])
        manifest.append({'file': path.name, 'bytes': path.stat().st_size,
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return pd.concat(sections, ignore_index=True), pd.DataFrame(audits), manifest


def aggregate(sections, weighted=True, outcome='gpa'):
    mask = sections.valid_gpa & sections.mapped
    if weighted:
        mask &= sections.valid_weight
    d = sections.loc[mask].copy()
    d['weight'] = d.enrollment if weighted else 1.
    d['weighted_gpa'] = d[outcome] * d.weight
    cells = d.groupby(['univ', 'field', 'year'], as_index=False).agg(
        numerator=('weighted_gpa', 'sum'), weight=('weight', 'sum'), n_sections=('gpa', 'size'))
    cells['mean'] = cells.numerator / cells.weight
    cells['year'] = cells.year.astype(int)
    return cells.drop(columns='numerator')


def spain_cells():
    crosswalk = pd.read_csv(ROOT/'data/mappings/spain_field_to_area.csv')
    d = pd.read_csv(ROOT/'data/raw/ministerio/Nota_Expediente_Grado_Univ.csv', sep=';', dtype=str)
    d.columns = ['univ', 'spanish_label', 'sex', 'indicator', 'period', 'value']
    d['spanish_label'] = d.spanish_label.str.replace(r'\s+', ' ', regex=True)
    d = d[(d.sex == 'Ambos sexos') & (d.univ != 'Total') & (d.indicator == 'Nota media')]
    d = d.merge(crosswalk, on='spanish_label', how='inner', validate='many_to_one')
    d['mean'] = pd.to_numeric(d.value.str.replace(',', '.'), errors='coerce')
    d['year'] = d.period.str[:4].astype(int)
    d = d.dropna(subset=['mean'])
    # Match ministry.load's pivot averaging before broad aggregation.
    d = d.groupby(['univ', 'spanish_field', 'field', 'year'], as_index=False)['mean'].mean()
    # Ministry means have no enrolment counts; weight original Spanish fields
    # equally within each broad university/area/year cell.
    return d.groupby(['univ', 'field', 'year'], as_index=False)['mean'].mean()


def compare(us, spain):
    shared = sorted(set(us.field) & set(spain.field))
    if len(shared) < 3:
        raise ValueError('At least three common fields required')
    # Refit BOTH models on the same field set, preserving sum-zero coding.
    u, ustats = field_effects(us[us.field.isin(shared)])
    s, sstats = field_effects(spain[spain.field.isin(shared)])
    table = s.rename(columns={'effect': 'spain_effect', 'se': 'spain_se'}).join(
        u.rename(columns={'effect': 'us_effect', 'se': 'us_se'})).sort_index()
    table.index.name = 'field'
    p, r = pearsonr(table.spain_effect, table.us_effect), spearmanr(table.spain_effect, table.us_effect)
    stats = {'n_common_areas': len(table), 'pearson_r': float(p.statistic),
             'spearman_rho': float(r.statistic), 'same_sign_areas': int((np.sign(table.spain_effect) == np.sign(table.us_effect)).sum()),
             'us_model': ustats, 'spain_model': sstats}
    return table, stats


def figure(table, stats, output):
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.axhline(0, color='0.8', lw=1); ax.axvline(0, color='0.8', lw=1)
    ax.scatter(table.spain_effect, table.us_effect, s=60, color='#2469a0')
    for i, (name, row) in enumerate(table.iterrows()):
        label = name.replace(', mathematics & computing', ', maths\n& computing').replace(' & architecture', '\n& architecture')
        offsets = {'Arts, media & architecture': (10, 20),
                   'Sports, tourism & services': (-12, 15), 'Agriculture': (-10, -17)}
        dx, dy = offsets.get(name, (6, 7 if i % 2 else -17))
        ax.annotate(label, (row.spain_effect, row.us_effect), xytext=(dx, dy),
                    ha='right' if dx < 0 else 'left', textcoords='offset points', fontsize=9)
    ax.margins(x=.36, y=.22)
    ax.set(xlabel='Spain: adjusted broad-area effect (grade points)',
           ylabel='US: adjusted broad-area effect (GPA points)',
           title=f"Field patterns across countries | Pearson r = {stats['pearson_r']:.2f}, Spearman ρ = {stats['spearman_rho']:.2f}")
    ax.spines[['right', 'top']].set_visible(False)
    fig.text(.08, .025, 'University + year fixed effects; equal weight per university–area–year cell.\nUS cell means weight sections/courses by enrolment. Broad-area comparison; not a causal estimate.', fontsize=9)
    fig.tight_layout(rect=[0, .07, 1, 1])
    for ext in ['png', 'pdf']:
        fig.savefig(output / f'us_spain_field_effects.{ext}', dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=ROOT/'data/raw/us33')
    parser.add_argument('--rebuild-mapping', action='store_true', help='Replace crosswalk with rule-generated version')
    args = parser.parse_args()
    res, fig, processed, maps = [ROOT / p for p in ['results', 'figures', 'data/processed', 'data/mappings']]
    for p in [res, fig, processed, maps]: p.mkdir(parents=True, exist_ok=True)
    mapping_path = maps / 'us_department_to_area.csv'
    if args.rebuild_mapping or not mapping_path.exists():
        build_mapping(args.raw_dir).to_csv(mapping_path, index=False)
    mapping = pd.read_csv(mapping_path, keep_default_na=False)
    if mapping.duplicated(['univ', 'department_code']).any():
        raise ValueError('Crosswalk must have unique university/department keys')
    if set(mapping.field) - {'', *SPANISH_TO_AREA.values()}:
        raise ValueError('Crosswalk contains an unknown broad area')
    print('Loading 33 institutions...', flush=True)
    sections, audit, manifest = load_sections(args.raw_dir, mapping)
    sections.to_csv(processed/'us_sections.csv.gz', index=False, compression='gzip')
    audit.to_csv(res/'us_data_audit.csv', index=False)
    usage = sections.groupby(['univ', 'department_code'], as_index=False).agg(rows=('gpa','size'), valid_gpa_rows=('valid_gpa','sum'))
    usage = usage.merge(mapping, on=['univ','department_code'], how='left', validate='one_to_one')
    usage.to_csv(res/'us_mapping_coverage.csv', index=False)
    us, es = aggregate(sections), spain_cells()
    us.to_csv(processed/'us_univ_field_year.csv', index=False)
    es.to_csv(processed/'spain_broad_univ_field_year.csv', index=False)
    print('Fitting comparable US and Spain models...', flush=True)
    table, stats = compare(us, es)
    table.to_csv(res/'us_spain_field_comparison.csv')
    table[['us_effect','us_se']].rename(columns={'us_effect':'effect','us_se':'se'}).to_csv(res/'us_field_effects.csv')
    stats['weighted_excluded_institutions'] = audit.loc[audit.usable_weighted.eq(0),'univ'].tolist()
    stats['raw_rows'] = int(audit.raw_rows.sum())
    stats['weighted_rows'] = int(audit.usable_weighted.sum())
    stats['mapping_coverage_valid_rows'] = float(sections.loc[sections.valid_gpa,'mapped'].mean())
    stats['us_year_range'] = [int(us.year.min()), int(us.year.max())]
    stats['spain_year_range'] = [int(es.year.min()), int(es.year.max())]
    sensitivity = {}
    for label, cells in [('equal_section_weights_all33', aggregate(sections, False)),
                         ('a_plus_capped_at4', aggregate(sections, outcome='gpa_a4'))]:
        _, sensitivity[label] = compare(cells, es)
    years = sorted(set(us.year) & set(es.year))
    if years:
        _, sensitivity['common_years'] = compare(us[us.year.isin(years)], es[es.year.isin(years)])
        sensitivity['common_years']['years'] = years
    print('Checking leave-one-university-out stability...', flush=True)
    leave_out = []
    for univ in sorted(us.univ.unique()):
        _, st = compare(us[us.univ.ne(univ)], es)
        leave_out.append({'omitted_university': univ, 'pearson_r': st['pearson_r'], 'spearman_rho': st['spearman_rho']})
    pd.DataFrame(leave_out).to_csv(res/'us_leave_one_university_out.csv', index=False)
    stats['sensitivity'] = sensitivity
    stats['leave_one_university_out_pearson_range'] = [min(s['pearson_r'] for s in leave_out), max(s['pearson_r'] for s in leave_out)]
    stats['model'] = 'OLS: mean ~ C(field, Sum) + C(univ) + C(year); unweighted university-area-year cells'
    stats['input_files'] = manifest
    stats['mapping_sha256'] = hashlib.sha256(mapping_path.read_bytes()).hexdigest()
    stats['workbook_sha256'] = hashlib.sha256((args.raw_dir/'dept_name_code_field_mapping.xlsx').read_bytes()).hexdigest()
    stats['limitations'] = ['Broad-area rather than 29-field replication; mapping requires subject-matter review.',
        'US course/section outcomes include multiple course levels; Spain uses graduates final averages.',
        'Four institutions have no enrolment counts; weighted analysis excludes them.',
        'Spanish sample follows ministry.py and is not restricted to public universities.',
        'Source blank grade categories are treated as zero, as in the released percentage tables.',
        'Conventional OLS standard errors match ministry.py; not university-clustered.',
        'Cross-area correlations are descriptive, based on only ten broad areas, not causal effects.']
    (res/'us_replication_stats.json').write_text(json.dumps(stats, indent=2), encoding='utf-8')
    figure(table, stats, fig)
    print(table.round(3).to_string())
    print(f"Pearson r={stats['pearson_r']:.4f}; Spearman rho={stats['spearman_rho']:.4f}", flush=True)

if __name__ == '__main__':
    main()
