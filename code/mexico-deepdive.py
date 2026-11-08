"""
Mexico deep dive: Mexico's role in U.S. trade in AI-related products.

Regenerates every number and figure in MEXICO-AI-TRADE.md (repo root).
Run from the repo root:  python code/mexico-deepdive.py

Conventions follow notebooks 06-11:
  - imports  : data-input/ALL-data-current.parquet (CON_VAL_MO, CAL_DUT_MO),
               classified with data-input/hs10_classification_final_v3.csv
  - exports  : data-input/All-country-exports.parquet (ALL_VAL_MO),
               classified with data-input/hs10_classification_imports_exports.csv
  - DF split : us-exports-hs10 repo, All-country-exports-DF.parquet
               (export_type = Total Exports / Domestic Exports / Re-Exports)
  - HS2 chapters 27, 71, 98, 99 excluded throughout
  - indices  : annualized monthly, 2023 = 100  ->  100 * 12 * x_t / sum(x_2023)

Writes: figures-mexico/*.png and *.pdf  (nothing under paper/ is touched)
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', 40)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGDIR = os.path.join(REPO, 'figures-mexico')
os.makedirs(FIGDIR, exist_ok=True)

DF_DIR_CANDIDATES = [
    os.path.join(REPO, 'data-input'),
    r'c:\heroku\us-exports-hs10\data\exports-hs10-DF',
    os.path.join(os.path.dirname(REPO), 'us-exports-hs10', 'data', 'exports-hs10-DF'),
]
DF_DIR = next((p for p in DF_DIR_CANDIDATES
               if os.path.exists(os.path.join(p, 'All-country-exports-DF.parquet'))), None)
if DF_DIR is None:
    raise FileNotFoundError('All-country-exports-DF.parquet not found in any of: '
                            + ', '.join(DF_DIR_CANDIDATES))

EXCL_HS2 = ['27', '71', '98', '99']
EXCL_CTY = ['TOTAL FOR ALL COUNTRIES', 'USMCA (NAFTA)', 'EUROPEAN UNION']

PALETTE = {'aggregate': 'black', 'primary': 'darkblue', 'secondary': '#8B0000',
           'tertiary': 'darkgreen', 'rank1': '#2E5090', 'rank2': '#4A90E2', 'rank3': '#7CB9E8'}


def hdr(t):
    print('\n' + '=' * 100)
    print(t)
    print('=' * 100)


def clean_axes(ax, lw=2):
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_linewidth(lw)
    ax.spines['bottom'].set_linewidth(lw)


def save(fig, name):
    fig.savefig(os.path.join(FIGDIR, name + '.png'), bbox_inches='tight')
    fig.savefig(os.path.join(FIGDIR, name + '.pdf'), bbox_inches='tight')
    plt.close(fig)
    print('  wrote', name + '.png/.pdf')


def prep(df, valcol, commcol, matlist, dutycol=None):
    df = df.rename(columns={commcol: 'HS10'})
    df['HS2'] = df['HS10'].astype(str).str.zfill(10).str[:2]
    df = df[~df['HS2'].isin(EXCL_HS2)].copy()
    df['HS10'] = df['HS10'].astype(str).str.zfill(10).astype('int64')
    df['time'] = pd.to_datetime(df['time'], format='%Y-%m')
    df['value'] = df[valcol].astype(float)
    if dutycol:
        df['duty'] = df[dutycol].astype(float)
    df = df.merge(matlist[['HS10', 'relevance', 'primary_category']], on='HS10', how='left')
    df['year'] = df['time'].dt.year
    return df


def idx2023(s):
    """Annualized monthly index, 2023 = 100."""
    return 100 * (12 * s / s.loc['2023'].sum())


def rate(d):
    """Effective duty rate in percent. Raises rather than emitting a silent NaN."""
    v = d['value'].sum()
    if not v > 0:
        raise ValueError(f'selection has no import value ({len(d)} rows); cannot form a duty rate')
    return 100 * d['duty'].sum() / v


def all_chapter_totals(path, valcol, commcol, filters=None):
    """Yearly totals with NO HS2 exclusions, for reporting alongside the ex-chapter series."""
    d = pd.read_parquet(path, columns=[valcol, commcol, 'time'], filters=filters)
    d['year'] = d['time'].str[:4].astype(int)
    return d[valcol].astype(float).groupby(d['year']).sum() / 1e9


# ---------------------------------------------------------------- load
mat_imp = pd.read_csv(os.path.join(REPO, 'data-input', 'hs10_classification_final_v3.csv')
                      ).rename(columns={'hs10_code': 'HS10'})
mat_exp = pd.read_csv(os.path.join(REPO, 'data-input', 'hs10_classification_imports_exports.csv')
                      ).rename(columns={'hs10_code': 'HS10'})

mx = prep(pd.read_parquet(os.path.join(REPO, 'data-input', 'ALL-data-current.parquet'),
                          filters=[('CTY_NAME', '==', 'MEXICO')]),
          'CON_VAL_MO', 'I_COMMODITY', mat_imp, 'CAL_DUT_MO')
us = prep(pd.read_parquet(os.path.join(REPO, 'data-input', 'TOTALdata-current.parquet')),
          'CON_VAL_MO', 'I_COMMODITY', mat_imp, 'CAL_DUT_MO')
exp_mx = prep(pd.read_parquet(os.path.join(REPO, 'data-input', 'All-country-exports.parquet'),
                              filters=[('CTY_NAME', '==', 'MEXICO')]),
              'ALL_VAL_MO', 'E_COMMODITY', mat_exp)
exp_df = prep(pd.read_parquet(os.path.join(DF_DIR, 'All-country-exports-DF.parquet'),
                              filters=[('CTY_NAME', '==', 'MEXICO')]),
              'ALL_VAL_MO', 'E_COMMODITY', mat_exp)

MXH = mx[mx.relevance == 'High']
USH = us[us.relevance == 'High']
EXH = exp_mx[exp_mx.relevance == 'High']
EH = exp_df[exp_df.relevance == 'High']
desc = mx[mx.year >= 2025].groupby('HS10')['I_COMMODITY_SDESC'].first()
cat_map = mat_imp.set_index('HS10')['primary_category']

hdr('0. DATA CHECKS')
print('DF directory:', DF_DIR)
print('imports  :', f'{len(mx):,}', 'rows |', mx.time.min().date(), '->', mx.time.max().date())
print('exports  :', f'{len(exp_mx):,}', 'rows |', exp_mx.time.min().date(), '->', exp_mx.time.max().date())
print('exports DF:', f'{len(exp_df):,}', 'rows |', exp_df.time.min().date(), '->', exp_df.time.max().date())
print('max duplicate (time, HS10) count:', mx.groupby(['time', 'HS10']).size().max(), '(should be 1)')
x = EH[EH.export_type == 'Total Exports'].groupby('year')['value'].sum() / 1e9
y = EXH.groupby('year')['value'].sum() / 1e9
print('\ncross-check AI exports to Mexico, DF file vs main export file ($B):')
print(pd.DataFrame({'DF_total': x, 'main_file': y}).loc[2022:].round(2).to_string())
unc = mx.groupby('year').apply(
    lambda d: 100 * d.loc[d.relevance.isna(), 'value'].sum() / d['value'].sum(), include_groups=False)
print('\nunclassified share of Mexico import value (%):',
      {int(k): round(v, 2) for k, v in unc.items() if k >= 2022})

hdr('1. LEVELS AND SHARES BY YEAR')
rows = []
for yr in [2022, 2023, 2024, 2025, 2026]:
    m_h = MXH[MXH.year == yr]['value'].sum()
    m_all = mx[mx.year == yr]['value'].sum()
    u_h = USH[USH.year == yr]['value'].sum()
    u_all = us[us.year == yr]['value'].sum()
    m_y = mx[mx.year == yr]
    rows.append(dict(year=yr, mx_ai=m_h / 1e9, mx_total=m_all / 1e9,
                     # mx_low is High/Medium/Low relevance "Low" only; mx_ex_ai is total minus AI,
                     # which additionally carries Medium-relevance and unclassified value.
                     mx_low=m_y[m_y.relevance == 'Low']['value'].sum() / 1e9,
                     mx_medium=m_y[m_y.relevance == 'Medium']['value'].sum() / 1e9,
                     mx_unclass=m_y[m_y.relevance.isna()]['value'].sum() / 1e9,
                     mx_ex_ai=(m_all - m_h) / 1e9,
                     ai_share_of_mx=100 * m_h / m_all,
                     mx_share_of_us_ai=100 * m_h / u_h,
                     us_ai=u_h / 1e9, us_total=u_all / 1e9))
lv = pd.DataFrame(rows).set_index('year')
print(lv.round(2).to_string())
assert np.allclose(lv.mx_low + lv.mx_medium + lv.mx_unclass + lv.mx_ai, lv.mx_total), \
    'relevance buckets do not add to the Mexico total'
print('(mx_low + mx_medium + mx_unclass + mx_ai = mx_total; mx_ex_ai = mx_total - mx_ai)')
print('\n2026 = Jan-Mar only. Growth rates:')
for a, b in [(2023, 2024), (2024, 2025), (2023, 2025)]:
    ma = MXH[MXH.year == a]['value'].sum()
    mb = MXH[MXH.year == b]['value'].sum()
    print(f'  Mexico AI {b} vs {a}: {100*(mb/ma-1):+.1f}%')
q = MXH[MXH.time.dt.month <= 3].groupby('year')['value'].sum() / 1e9
qu = USH[USH.time.dt.month <= 3].groupby('year')['value'].sum() / 1e9
print(f'  Mexico AI Q1-2026 vs Q1-2025: {100*(q.loc[2026]/q.loc[2025]-1):+.1f}%'
      f'   (U.S. AI: {100*(qu.loc[2026]/qu.loc[2025]-1):+.1f}%)')

hdr('2. CONTRIBUTION TO U.S. AI IMPORT GROWTH, 2023 -> 2025')
ctry = prep(pd.read_parquet(os.path.join(REPO, 'data-input', 'ALL-data-current.parquet'),
                            filters=[('time', '>=', '2023-01')]),
            'CON_VAL_MO', 'I_COMMODITY', mat_imp)
ctry = ctry[(ctry.relevance == 'High') & (~ctry.CTY_NAME.isin(EXCL_CTY))]
d_us = USH[USH.year == 2025]['value'].sum() - USH[USH.year == 2023]['value'].sum()
rows = []
for c, g in ctry.groupby('CTY_NAME', observed=True):
    dd = g[g.year == 2025]['value'].sum() - g[g.year == 2023]['value'].sum()
    rows.append(dict(country=c, delta_bn=dd / 1e9, pct_of_us_increase=100 * dd / d_us))
con = pd.DataFrame(rows).sort_values('delta_bn', ascending=False)
print(f'U.S. AI-high import increase 2023->2025: ${d_us/1e9:,.1f}B')
print(con.head(8).round(1).to_string(index=False))

hdr('3. COMPOSITION: MEXICO AI IMPORTS BY CATEGORY')
rows = []
for c in [x for x in MXH.primary_category.dropna().unique() if x != 'Not_DC_Related']:
    d = MXH[MXH.primary_category == c]
    u = USH[USH.primary_category == c]
    a, b = d[d.year == 2023]['value'].sum(), d[d.year == 2025]['value'].sum()
    ua, ub = u[u.year == 2023]['value'].sum(), u[u.year == 2025]['value'].sum()
    rows.append(dict(category=c.replace('_', ' '), mx_2023=a / 1e9, mx_2025=b / 1e9,
                     growth=100 * (b / a - 1) if a else np.nan,
                     share_of_mx_ai_2025=100 * b / MXH[MXH.year == 2025]['value'].sum(),
                     mx_share_of_us_2023=100 * a / ua if ua else np.nan,
                     mx_share_of_us_2025=100 * b / ub if ub else np.nan,
                     us_growth=100 * (ub / ua - 1) if ua else np.nan))
cat = pd.DataFrame(rows).sort_values('mx_2025', ascending=False)
print(cat.round(1).to_string(index=False))

print('\nMexico rank among source countries, by category (2025):')
print('Shares are of TOTAL U.S. imports in the category, the same denominator as the table above.')
print('Ranks come from the 30 countries in the country-level file; "rank_safe" is True when the')
print('value NOT covered by that file is smaller than Mexico\'s, so no missing country can outrank it.')
for c in ['Compute_Hardware', 'Electrical_Power', 'Networking_Telecom', 'Cooling_HVAC',
          'Building_Structure', 'Fire_Safety_Security']:
    s = ctry[(ctry.primary_category == c) & (ctry.year == 2025)].groupby('CTY_NAME', observed=True)['value'].sum()
    s = s.sort_values(ascending=False)
    us_tot = USH[(USH.primary_category == c) & (USH.year == 2025)]['value'].sum()
    rank = list(s.index).index('MEXICO') + 1
    resid = us_tot - s.sum()
    top = ' | '.join(f'{k} {100*v/us_tot:.1f}%' for k, v in s.head(3).items())
    print(f'  {c:22s} rank={rank}  ->  {top}')
    print(f'  {"":22s}   file covers {100*s.sum()/us_tot:.0f}% of U.S. imports here; '
          f'uncovered ${resid/1e9:.1f}B vs Mexico ${s["MEXICO"]/1e9:.1f}B  ->  '
          f'rank_safe={resid < s["MEXICO"]}')

hdr('4. TOP AI PRODUCTS IMPORTED FROM MEXICO (2025)')
g25 = MXH[MXH.year == 2025].groupby('HS10')['value'].sum().sort_values(ascending=False)
g23 = MXH[MXH.year == 2023].groupby('HS10')['value'].sum()
u25 = USH[USH.year == 2025].groupby('HS10')['value'].sum()
rows = []
for h in g25.head(15).index:
    a, b = g23.get(h, 0.0), g25[h]
    rows.append(dict(HS10=h, description=str(desc.get(h, ''))[:50],
                     category=str(cat_map.get(h, '')).replace('_', ' '),
                     y2023=a / 1e9, y2025=b / 1e9,
                     growth=100 * (b / a - 1) if a > 0 else np.nan,
                     share_of_mx_ai=100 * b / g25.sum(),
                     mx_share_of_us_imports=100 * b / u25.get(h, np.nan)))
top15 = pd.DataFrame(rows)
print(top15.round(1).to_string(index=False))

# Union the two indices: reindexing on g25 alone would silently drop codes that traded in
# 2023 but not 2025, so the contributions would be measured against too large a denominator.
codes = g25.index.union(g23.index)
delta = (g25.reindex(codes).fillna(0) - g23.reindex(codes).fillna(0)).sort_values(ascending=False)
d_mx = MXH[MXH.year == 2025]['value'].sum() - MXH[MXH.year == 2023]['value'].sum()
assert abs(delta.sum() - d_mx) < 1e-6 * abs(d_mx), 'code-level deltas do not sum to the aggregate change'
print(f'\nMexico AI import increase 2023->2025: ${d_mx/1e9:.1f}B '
      f'(= {g25.sum()/1e9:.1f} - {g23.sum()/1e9:.1f})')
print('Top 5 contributors to that increase:')
for h in delta.head(5).index:
    print(f'  {h}  {str(desc.get(h,""))[:46]:48s} +${delta[h]/1e9:6.2f}B '
          f'({100*delta[h]/d_mx:4.1f}% of Mexico AI growth, '
          f'{100*delta[h]/d_us:4.1f}% of U.S. AI growth)')

print('\nConcentration of 2025 AI imports:')
for c in ['MEXICO', 'TAIWAN', 'CHINA']:
    s = ctry[(ctry.CTY_NAME == c) & (ctry.year == 2025)].groupby('HS10')['value'].sum().sort_values(ascending=False)
    tot = s.sum()
    print(f'  {c:7s} ${tot/1e9:7.1f}B | codes={len(s):4d} | top1={100*s.iloc[0]/tot:5.1f}% '
          f'| top5={100*s.head(5).sum()/tot:5.1f}% | HHI={((s/tot)**2).sum()*1e4:6.0f}')

hdr('5. U.S. EXPORTS TO MEXICO: DOMESTIC vs RE-EXPORTS')
piv = EH.pivot_table(index='year', columns='export_type', values='value', aggfunc='sum') / 1e9
piv = piv[['Total Exports', 'Domestic Exports', 'Re-Exports']]
piv['reexport_share'] = 100 * piv['Re-Exports'] / piv['Total Exports']
allx = exp_df.pivot_table(index='year', columns='export_type', values='value', aggfunc='sum') / 1e9
piv['ai_share_of_exports_to_mx'] = 100 * piv['Total Exports'] / allx['Total Exports']
piv['reexport_share_all_products'] = 100 * allx['Re-Exports'] / allx['Total Exports']
print(piv.round(2).to_string())
print('NOTE: ai_share_of_exports_to_mx divides by exports EXCLUDING HS2 27/71/98/99.')
exp_all_ch = all_chapter_totals(os.path.join(REPO, 'data-input', 'All-country-exports.parquet'),
                                'ALL_VAL_MO', 'E_COMMODITY', [('CTY_NAME', '==', 'MEXICO')])
print('  same share against ALL chapters: ' + '  '.join(
    f'{y}: {100*piv.loc[y, "Total Exports"]/exp_all_ch.loc[y]:.1f}%' for y in piv.index))
for col in ['Total Exports', 'Domestic Exports', 'Re-Exports']:
    print(f'  {col:17s} 2025 vs 2023: {100*(piv.loc[2025,col]/piv.loc[2023,col]-1):+.1f}%')

rows = []
for c in [x for x in EH.primary_category.dropna().unique() if x != 'Not_DC_Related']:
    d25 = EH[(EH.primary_category == c) & (EH.year == 2025)].groupby('export_type')['value'].sum()
    d23 = EH[(EH.primary_category == c) & (EH.year == 2023)].groupby('export_type')['value'].sum()
    tot = d25.get('Total Exports', 0)
    if tot / 1e9 < 0.05:
        continue
    rows.append(dict(category=c.replace('_', ' '), total_2025=tot / 1e9,
                     reexports_2025=d25.get('Re-Exports', 0) / 1e9,
                     reexport_share_2025=100 * d25.get('Re-Exports', 0) / tot,
                     reexport_share_2023=100 * d23.get('Re-Exports', 0) / d23.get('Total Exports', np.nan),
                     growth_total=100 * (tot / d23.get('Total Exports', np.nan) - 1)))
print('\nBy category:')
print(pd.DataFrame(rows).sort_values('total_2025', ascending=False).round(1).to_string(index=False))

hdr('6. ROUND TRIP: COMPONENTS OUT, ASSEMBLED UNITS BACK')
re25 = EH[(EH.year == 2025) & (EH.export_type == 'Re-Exports')].groupby('HS10')['value'].sum().sort_values(ascending=False)
tot25 = EH[(EH.year == 2025) & (EH.export_type == 'Total Exports')].groupby('HS10')['value'].sum()
re23 = EH[(EH.year == 2023) & (EH.export_type == 'Re-Exports')].groupby('HS10')['value'].sum()
edesc = exp_df[exp_df.year >= 2025].groupby('HS10')['E_COMMODITY_SDESC'].first()

# The two hand-picked baskets that define the round trip. Everything printed below and the
# round-trip figure use exactly these lists, so the tables in the write-up reconcile to the bars.
COMPONENTS = [8473300002, 8542310045, 8523510000, 8471704065, 8542310050,
              8542390060, 8542310075, 8542320070, 8542330000, 8542310040]
UNITS = [8471500150, 8471709000, 8471804000, 8473301180, 8471809000]

rows = []
for h in re25.head(12).index:
    rows.append(dict(HS10=h, description=str(edesc.get(h, ''))[:50],
                     category=str(mat_exp.set_index('HS10')['primary_category'].get(h, '')).replace('_', ' '),
                     reexports_2025=re25[h] / 1e9, reexports_2023=re23.get(h, 0) / 1e9,
                     reexport_share_of_code=100 * re25[h] / tot25.get(h, np.nan),
                     imports_back_from_mx=g25.get(h, 0) / 1e9,
                     basket='component' if h in COMPONENTS else ('unit' if h in UNITS else '-')))
print('Top AI codes re-exported to Mexico (2025).  NOTE: this is the largest re-export codes,')
print('NOT the component basket - the "basket" column says which of these the round trip counts.')
print(pd.DataFrame(rows).round(2).to_string(index=False))

both = pd.DataFrame({'reexports_to_mx': re25, 'imports_from_mx': g25}).fillna(0)
n_re = (both.reexports_to_mx > 0).sum()
n_both = ((both.reexports_to_mx > 0) & (both.imports_from_mx > 0)).sum()
print(f'\nAI-high codes re-exported to Mexico in 2025: {n_re}; also imported back under the same code: {n_both}')

comp_out = (EH[(EH.export_type == 'Re-Exports') & (EH.HS10.isin(COMPONENTS))]
            .groupby('year')['value'].sum() / 1e9)
units_in = MXH[MXH.HS10.isin(UNITS)].groupby('year')['value'].sum() / 1e9

# Full membership of both baskets, so the figure's two bars are reproducible line by line.
print('\nCOMPONENT basket - U.S. re-exports to Mexico, $B (these sum to the left-hand bar):')
crows = []
for h in COMPONENTS:
    s = (EH[(EH.export_type == 'Re-Exports') & (EH.HS10 == h)]
         .groupby('year')['value'].sum() / 1e9)
    crows.append(dict(HS10=h, description=str(edesc.get(h, ''))[:44],
                      y2023=s.get(2023, 0.0), y2025=s.get(2025, 0.0)))
cdf = pd.DataFrame(crows).sort_values('y2025', ascending=False)
print(cdf.round(3).to_string(index=False))
print(f'  TOTAL  2023: ${cdf.y2023.sum():.2f}B   2025: ${cdf.y2025.sum():.2f}B')

print('\nUNIT basket - U.S. imports from Mexico, $B (these sum to the right-hand bar):')
urows = []
for h in UNITS:
    s = MXH[MXH.HS10 == h].groupby('year')['value'].sum() / 1e9
    urows.append(dict(HS10=h, description=str(desc.get(h, ''))[:44],
                      y2023=s.get(2023, 0.0), y2025=s.get(2025, 0.0)))
udf = pd.DataFrame(urows).sort_values('y2025', ascending=False)
print(udf.round(3).to_string(index=False))
print(f'  TOTAL  2023: ${udf.y2023.sum():.2f}B   2025: ${udf.y2025.sum():.2f}B')

rt = pd.DataFrame({'components_reexported_to_mx': comp_out, 'units_imported_from_mx': units_in}).dropna()
rt['ratio'] = rt.units_imported_from_mx / rt.components_reexported_to_mx
rt['gap_bn'] = rt.units_imported_from_mx - rt.components_reexported_to_mx
assert abs(cdf.y2025.sum() - rt.loc[2025, 'components_reexported_to_mx']) < 1e-6
assert abs(udf.y2025.sum() - rt.loc[2025, 'units_imported_from_mx']) < 1e-6
print('\nComponents out vs assembled units back ($B):')
print(rt.round(2).to_string())

rows = []
for yr in [2022, 2023, 2024, 2025, 2026]:
    re_y = EH[(EH.year == yr) & (EH.export_type == 'Re-Exports')]['value'].sum()
    imp_y = MXH[MXH.year == yr]['value'].sum()
    rows.append(dict(year=yr, ai_reexports_to_mx=re_y / 1e9, ai_imports_from_mx=imp_y / 1e9,
                     reexports_per_dollar_imported=re_y / imp_y))
print('\nRound-trip intensity:')
print(pd.DataFrame(rows).round(2).to_string(index=False))

hdr('7. BILATERAL BALANCE')
rows = []
for yr in [2022, 2023, 2024, 2025, 2026]:
    i_all = mx[mx.year == yr]['value'].sum()
    i_ai = MXH[MXH.year == yr]['value'].sum()
    e_all = exp_mx[exp_mx.year == yr]['value'].sum()
    e_ai = EXH[EXH.year == yr]['value'].sum()
    rows.append(dict(year=yr, imports=i_all / 1e9, exports=e_all / 1e9, balance=(e_all - i_all) / 1e9,
                     ai_balance=(e_ai - i_ai) / 1e9,
                     nonai_balance=((e_all - e_ai) - (i_all - i_ai)) / 1e9))
bal = pd.DataFrame(rows).set_index('year')
print(bal.round(1).to_string())
d = bal.loc[2025] - bal.loc[2023]
print(f'\nChange 2023->2025: balance {d.balance:+.1f}B | AI {d.ai_balance:+.1f}B | non-AI {d.nonai_balance:+.1f}B')
print(f'AI share of the widening bilateral deficit: {100*d.ai_balance/d.balance:.0f}%')

# The figures above exclude HS2 27/71/98/99, matching the paper. Chapter 27 alone is a large
# U.S. export to Mexico, so the all-chapter balance is a materially different number and the
# AI share of the widening is sensitive to which one is quoted. Report both.
imp_all = all_chapter_totals(os.path.join(REPO, 'data-input', 'ALL-data-current.parquet'),
                             'CON_VAL_MO', 'I_COMMODITY', [('CTY_NAME', '==', 'MEXICO')])
exp_all = all_chapter_totals(os.path.join(REPO, 'data-input', 'All-country-exports.parquet'),
                             'ALL_VAL_MO', 'E_COMMODITY', [('CTY_NAME', '==', 'MEXICO')])
ballx = (exp_all - imp_all)
print('\nAll-chapter comparison (no HS2 exclusions):')
print(pd.DataFrame({'imports': imp_all, 'exports': exp_all, 'balance': ballx}).loc[2022:].round(1).to_string())
d_all = ballx.loc[2025] - ballx.loc[2023]
print(f'  widening 2023->2025: ex-chapter {d.balance:+.1f}B  vs  all-chapter {d_all:+.1f}B')
print(f'  AI share of the widening: ex-chapter {100*d.ai_balance/d.balance:.0f}%  '
      f'vs  all-chapter {100*d.ai_balance/d_all:.0f}%')

hdr('8. TARIFFS AND EXEMPTIONS')
rows = []
for lbl, sel in [('2024', mx.year == 2024),
                 ('2025 H1', (mx.year == 2025) & (mx.time.dt.month <= 6)),
                 ('2025 H2', (mx.year == 2025) & (mx.time.dt.month > 6)),
                 ('Dec 2025', (mx.year == 2025) & (mx.time.dt.month == 12)),
                 ('2026 Q1', mx.year == 2026)]:
    d = mx[sel]
    r = {rel: rate(d[d.relevance == rel]) for rel in ['High', 'Low']}
    rows.append(dict(period=lbl, mexico_ai=r['High'], mexico_nonai=r['Low']))
tar = pd.DataFrame(rows)
assert tar[['mexico_ai', 'mexico_nonai']].notna().all().all(), 'a tariff period produced no rate'
for lbl, sel in [('2024', us.year == 2024), ('Dec 2025', (us.year == 2025) & (us.time.dt.month == 12))]:
    d = us[sel]
    print(f'  U.S. overall AI-high effective rate, {lbl}: {rate(d[d.relevance == "High"]):.2f}%')
print(tar.round(2).to_string(index=False))

rows = []
for c in ['Compute_Hardware', 'Electrical_Power', 'Networking_Telecom', 'Cooling_HVAC']:
    d = MXH[MXH.primary_category == c]
    r = {}
    for lbl, sel in [('y2024', d.year == 2024), ('dec2025', (d.year == 2025) & (d.time.dt.month == 12)),
                     ('q1_2026', d.year == 2026)]:
        r[lbl] = rate(d[sel])
    rows.append(dict(category=c.replace('_', ' '), **r))
print('\nMexico AI-high effective rate by category:')
print(pd.DataFrame(rows).round(2).to_string(index=False))

ce = pd.read_csv(os.path.join(REPO, 'data-input', 'tariff-exemption-lists',
                              'consumer_electronics_EO14257_apr11.csv'))
an = pd.read_csv(os.path.join(REPO, 'data-input', 'tariff-exemption-lists', 'annex-II-exemptions.csv'))
s122 = pd.read_csv(os.path.join(REPO, 'data-input', 'tariff-exemption-lists',
                                'section122-product-exemptions.csv'))
codes10 = set(ce['HTSUS'].astype(str).str.strip()) | set(an['HTSUS'].astype(str).str.strip())
s122['hts_code'] = s122['hts_code'].astype(str).str.strip()
codes10 |= set(s122[s122.digits == 10]['hts_code'])
codes8 = set(s122[s122.digits == 8]['hts_code'])
for name, frame in [('Mexico', MXH), ('U.S. total', USH)]:
    d = frame[frame.year == 2025].copy()
    s = d['HS10'].astype(str)
    on = s.isin(codes10) | s.str[:8].isin(codes8)
    print(f'\n{name} AI-high 2025 imports ${d["value"].sum()/1e9:.1f}B, '
          f'on an exemption list: {100*d.loc[on,"value"].sum()/d["value"].sum():.1f}%')

# ---------------------------------------------------------------- figures
hdr('9. FIGURES')
mx_ai_m = MXH.groupby('time')['value'].sum()
mx_low_m = mx[mx.relevance == 'Low'].groupby('time')['value'].sum()
us_ai_m = USH.groupby('time')['value'].sum()

fig, ax = plt.subplots(figsize=(15, 9))
for s, lab, col in [(us_ai_m, 'U.S. AI-Related Imports (all sources)', PALETTE['aggregate']),
                    (mx_ai_m, 'AI-Related Imports from Mexico', PALETTE['primary']),
                    (mx_low_m, 'Non-AI Imports from Mexico', PALETTE['secondary'])]:
    i = idx2023(s)
    ax.plot(i.index, i.values, color=col, alpha=0.7, linewidth=6, label=lab)
    ax.annotate(f'{i.iloc[-1]:.1f}', xy=(i.index[-1], i.iloc[-1]), xytext=(10, 0),
                textcoords='offset points', fontsize=14, fontweight='bold', color=col, va='center')
ax.set_title('Imports from Mexico: AI-Related vs Everything Else', fontsize=20, fontweight='bold', pad=20)
ax.set_ylabel('Monthly Index, 2023 = 100', fontsize=16, fontweight='bold')
ax.set_xlim([pd.Timestamp('2022-01-01'), mx_ai_m.index[-1] + pd.Timedelta(days=95)])
ax.tick_params(axis='x', labelsize=16, rotation=25)
ax.tick_params(axis='y', labelsize=16)
clean_axes(ax, 3)
ax.legend(fontsize=16, frameon=False, loc='upper left')
save(fig, 'mexico-ai-index')

fig, ax = plt.subplots(figsize=(12, 6))
cc = cat.sort_values('mx_2025', ascending=False).head(5)
x = np.arange(len(cc))
w = 0.35
b1 = ax.bar(x - w / 2, cc.mx_2023, w, color=PALETTE['rank3'], edgecolor='black', linewidth=1.5, label='2023')
b2 = ax.bar(x + w / 2, cc.mx_2025, w, color=PALETTE['rank1'], edgecolor='black', linewidth=1.5, label='2025')
for bars in [b1, b2]:
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
                f'${bar.get_height():.1f}B', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylabel('Imports from Mexico ($B)', fontsize=16, fontweight='bold')
ax.set_title('AI-Related Imports from Mexico by Category', fontsize=18, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels([c.replace(' ', '\n') for c in cc.category])
ax.set_ylim(0, cc.mx_2025.max() * 1.25)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.tick_params(axis='x', labelsize=12)
ax.tick_params(axis='y', labelsize=12)
for label in ax.get_xticklabels():
    label.set_fontweight('bold')
clean_axes(ax)
ax.legend(fontsize=12, frameon=False, loc='upper right')
save(fig, 'mexico-ai-by-category')

fig, ax = plt.subplots(figsize=(12, 6))
yrs = [2022, 2023, 2024, 2025]
x = np.arange(len(yrs))
w = 0.35
dom = piv.loc[yrs, 'Domestic Exports']
ree = piv.loc[yrs, 'Re-Exports']
b1 = ax.bar(x - w / 2, dom, w, color=PALETTE['tertiary'], edgecolor='black', linewidth=1.5,
            label='Domestic Exports')
b2 = ax.bar(x + w / 2, ree, w, color=PALETTE['secondary'], edgecolor='black', linewidth=1.5,
            label='Re-Exports')
for bars in [b1, b2]:
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f'${bar.get_height():.1f}B', ha='center', va='bottom', fontsize=11, fontweight='bold')
for i, yr in enumerate(yrs):
    ax.text(i, ree.loc[yr] + 5.5, f'{piv.loc[yr, "reexport_share"]:.0f}%\nre-export',
            ha='center', va='bottom', fontsize=11, fontweight='bold', color=PALETTE['secondary'])
ax.set_ylabel('U.S. AI-Related Exports to Mexico ($B)', fontsize=15, fontweight='bold')
ax.set_title('U.S. AI-Related Exports to Mexico: Domestic vs Re-Exports', fontsize=18,
             fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(yrs)
ax.set_ylim(0, ree.max() * 1.40)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.tick_params(axis='x', labelsize=13)
ax.tick_params(axis='y', labelsize=12)
for label in ax.get_xticklabels():
    label.set_fontweight('bold')
clean_axes(ax)
ax.legend(fontsize=12, frameon=False, loc='upper left')
save(fig, 'mexico-reexports')

fig, ax = plt.subplots(figsize=(12, 6))
r = rt.loc[[y for y in [2022, 2023, 2024, 2025] if y in rt.index]]
x = np.arange(len(r))
w = 0.35
b1 = ax.bar(x - w / 2, r.components_reexported_to_mx, w, color=PALETTE['rank2'],
            edgecolor='black', linewidth=1.5, label='Components re-exported to Mexico')
b2 = ax.bar(x + w / 2, r.units_imported_from_mx, w, color=PALETTE['rank1'],
            edgecolor='black', linewidth=1.5, label='Assembled units imported from Mexico')
for bars in [b1, b2]:
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.0,
                f'${bar.get_height():.1f}B', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylabel('Value ($B)', fontsize=16, fontweight='bold')
ax.set_title('Chips and Boards Out, Assembled Units Back', fontsize=18, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(r.index.astype(int))
ax.set_ylim(0, r.units_imported_from_mx.max() * 1.30)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.tick_params(axis='x', labelsize=13)
ax.tick_params(axis='y', labelsize=12)
for label in ax.get_xticklabels():
    label.set_fontweight('bold')
clean_axes(ax)
ax.legend(fontsize=12, frameon=False, loc='upper left')
save(fig, 'mexico-round-trip')

print('\nDONE')
