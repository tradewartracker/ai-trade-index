"""
Where the round trip crosses the border.

Pulls Census port/district detail to locate the U.S.-Mexico AI round trip in space
and follow how it evolved, 2022 through 2026 Q1:

  - exit districts for U.S. re-exports to Mexico of parts (8473300002) and CPUs (8542310045)
  - entry districts and ports for U.S. imports of servers from Mexico (8471500150 / HS6 847150)

Run from the repo root:  python code/mexico-ports.py

Endpoint notes:
  - imports/hs and exports/hs carry DISTRICT at full HS10; exports/hs also carries the
    domestic/re-export flag (DF: 1 = domestic, 2 = re-export, '-' = total)
  - imports/porths carries PORT but only to HS6; HS10 returns 204 No Content
  - `time=YYYY` returns all twelve months in one call
  - a Census API key is required; set CENSUS_API_KEY or pass --key

Writes: figures-mexico/mexico-border-crossings.png/.pdf, a single panel showing the El Paso
corridor, and caches raw pulls under data-input/census-ports/. The Juarez-vs-Laredo port
shares are printed as a table rather than plotted. Nothing under paper/ is touched.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', 40)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO, 'data-input', 'census-ports')
FIGDIR = os.path.join(REPO, 'figures-mexico')
os.makedirs(CACHE, exist_ok=True)
os.makedirs(FIGDIR, exist_ok=True)

BASE = 'https://api.census.gov/data/timeseries/intltrade/'
MEXICO_CTY = '2010'
YEARS = [2022, 2023, 2024, 2025, 2026]

# Census split the omnibus processor code 8542310001 into the 8542310015-0075 family in
# July 2024, so the CPU-specific HS10 (8542310045) only exists from 2024H2. For a series
# that spans 2022-2026 we use HS6 854231, processors and controllers.
PARTS, CPUS, SERVERS = '8473300002', '854231', '8471500150'
CPUS_HS10 = '8542310045'
SERVERS_HS6 = '847150'
LEVEL = {PARTS: 'HS10', CPUS: 'HS6', CPUS_HS10: 'HS10'}
LABEL = {PARTS: 'Parts for ADP machines', CPUS: 'Processors and controllers',
         CPUS_HS10: 'CPUs (HS10, 2024H2 onward)', SERVERS: 'Processing units (servers)'}
DF_FLAG = {'1': 'Domestic', '2': 'Re-export', '-': 'Total'}

# El Paso customs district covers the Juarez-facing bridges. Matched on exact port names, not
# substrings: an unanchored 'COLUMBUS' matches COLUMBUS, OH (Columbus, NM does not appear in
# this series at all), and an unanchored 'EL PASO' would be fine here but is the same hazard.
JUAREZ_PORTS = ['YSLETA, TX', 'SANTA TERESA, NM', 'EL PASO, TX', 'FABENS, TX', 'COLUMBUS, NM']
LAREDO_PORTS = ['LAREDO, TX']
EL_PASO_DISTRICT = 'EL PASO, TX'


def get_key(cli_key=None):
    key = cli_key or os.environ.get('CENSUS_API_KEY')
    if key:
        return key
    # fall back to the key already used by the sister download pipelines
    import re
    for p in [r'C:\heroku\us-exports-hs10\make-exports-hs10-DF-dataset.ipynb',
              r'C:\heroku\how-restrictive-us-trade\make-imports-hs10-dataset-current-month.ipynb']:
        if os.path.exists(p):
            m = re.search(r'key=([A-Za-z0-9]{20,})', open(p, encoding='utf-8').read())
            if m:
                return m.group(1)
    raise SystemExit('No Census API key. Set CENSUS_API_KEY or pass --key. '
                     'Free signup: https://api.census.gov/data/key_signup.html')


def fetch(endpoint, params, key, retries=4):
    p = dict(params)
    p['key'] = key
    url = BASE + endpoint + '?' + urllib.parse.urlencode(p)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=240) as r:
                if r.status == 204:
                    return []
                d = json.load(r)
            return [dict(zip(d[0], row)) for row in d[1:]]
        except urllib.error.HTTPError as e:
            if attempt == retries - 1:
                print(f'  ERROR {endpoint} {params}: {e}')
                return []
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            if attempt == retries - 1:
                print(f'  ERROR {endpoint} {params}: {e}')
                return []
            time.sleep(5)
    return []


def cached(name, endpoint, params, key, force=False):
    path = os.path.join(CACHE, name + '.parquet')
    if os.path.exists(path) and not force:
        return pd.read_parquet(path)
    rows = fetch(endpoint, params, key)
    if not rows:
        print(f'  no data: {name}')
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)
    print(f'  saved {name}.parquet ({len(df)} rows)')
    time.sleep(1)
    return df


def tidy(df, valcol, namecol='DIST_NAME'):
    if not len(df):
        return df
    df = df[(df.get('DISTRICT', pd.Series(dtype=str)) != '-') if 'DISTRICT' in df else
            (df['PORT'] != '-')].copy()
    df = df[df[namecol].notna() & (df[namecol].str.strip() != '')]
    df['place'] = df[namecol].str.strip()
    df['value'] = df[valcol].astype(float)
    df['year'] = df['time'].str[:4].astype(int)
    return df


def main(force=False, key=None):
    key = get_key(key)

    print('Downloading (cached under data-input/census-ports/)')
    exits, entries, ports = [], [], []
    for yr in YEARS:
        for code in (PARTS, CPUS, CPUS_HS10):
            d = cached(f'exp_district_{code}_{yr}', 'exports/hs',
                       {'get': 'DISTRICT,DIST_NAME,DF,ALL_VAL_MO', 'time': str(yr),
                        'CTY_CODE': MEXICO_CTY, 'E_COMMODITY': code,
                        'COMM_LVL': LEVEL[code]}, key, force)
            if len(d):
                d['code'] = code
                exits.append(d)
        d = cached(f'imp_district_{SERVERS}_{yr}', 'imports/hs',
                   {'get': 'DISTRICT,DIST_NAME,CON_VAL_MO', 'time': str(yr),
                    'CTY_CODE': MEXICO_CTY, 'I_COMMODITY': SERVERS, 'COMM_LVL': 'HS10'}, key, force)
        if len(d):
            entries.append(d)
        d = cached(f'imp_port_{SERVERS_HS6}_{yr}', 'imports/porths',
                   {'get': 'PORT,PORT_NAME,GEN_VAL_MO', 'time': str(yr),
                    'CTY_CODE': MEXICO_CTY, 'I_COMMODITY': SERVERS_HS6, 'COMM_LVL': 'HS6'}, key, force)
        if len(d):
            ports.append(d)

    ex = tidy(pd.concat(exits, ignore_index=True), 'ALL_VAL_MO')
    en = tidy(pd.concat(entries, ignore_index=True), 'CON_VAL_MO')
    po = tidy(pd.concat(ports, ignore_index=True), 'GEN_VAL_MO', namecol='PORT_NAME')
    ex['flag'] = ex['DF'].map(DF_FLAG)

    # ---------------------------------------------------------------- exits
    for code in (PARTS, CPUS, CPUS_HS10):
        d = ex[(ex.code == code) & (ex.flag == 'Re-export')]
        if not len(d):
            continue
        piv = d.pivot_table(index='place', columns='year', values='value', aggfunc='sum').fillna(0) / 1e9
        piv = piv.loc[piv[max(piv.columns)].sort_values(ascending=False).index].head(6)
        tot = d.groupby('year')['value'].sum() / 1e9
        print(f'\n=== EXITS | U.S. re-exports to Mexico of {LABEL[code]} ({code}), $B ===')
        print(piv.round(2).to_string())
        print('  total   ' + '  '.join(f'{y}: {tot.get(y, np.nan):.2f}' for y in sorted(tot.index)))
        shr = 100 * piv.loc[[i for i in piv.index if i == EL_PASO_DISTRICT]].sum() / tot
        print('  El Paso share (%): ' + '  '.join(f'{y}: {shr.get(y, np.nan):.1f}' for y in sorted(tot.index)))
        dom = ex[(ex.code == code) & (ex.flag == 'Domestic')].groupby('year')['value'].sum() / 1e9
        print('  (domestic exports, $B): ' + '  '.join(f'{y}: {dom.get(y, 0):.2f}' for y in sorted(tot.index)))

    # ---------------------------------------------------------------- entries
    piv = en.pivot_table(index='place', columns='year', values='value', aggfunc='sum').fillna(0) / 1e9
    piv = piv.loc[piv[max(piv.columns)].sort_values(ascending=False).index].head(6)
    tot = en.groupby('year')['value'].sum() / 1e9
    print(f'\n=== ENTRIES | U.S. imports of {LABEL[SERVERS]} from Mexico, by district, $B ===')
    print(piv.round(2).to_string())
    print('  total   ' + '  '.join(f'{y}: {tot.get(y, np.nan):.2f}' for y in sorted(tot.index)))

    pp = po.pivot_table(index='place', columns='year', values='value', aggfunc='sum').fillna(0) / 1e9
    pp = pp.loc[pp[max(pp.columns)].sort_values(ascending=False).index].head(8)
    ptot = po.groupby('year')['value'].sum() / 1e9
    print(f'\n=== ENTRIES | HS6 {SERVERS_HS6} from Mexico, by port of entry, $B ===')
    print(pp.round(2).to_string())
    jz = po[po.place.isin(JUAREZ_PORTS)].groupby('year')['value'].sum() / 1e9
    lo = po[po.place.isin(LAREDO_PORTS)].groupby('year')['value'].sum() / 1e9
    unmatched = sorted(set(po.place) - set(JUAREZ_PORTS) - set(LAREDO_PORTS))
    print(f'  ({len(unmatched)} other ports carry '
          f'{100*po[~po.place.isin(JUAREZ_PORTS + LAREDO_PORTS)].value.sum()/po.value.sum():.1f}% of the total)')
    print('  total       ' + '  '.join(f'{y}: {ptot.get(y, np.nan):7.2f}' for y in sorted(ptot.index)))
    print('  Juarez %    ' + '  '.join(f'{y}: {100*jz.get(y, np.nan)/ptot.get(y, np.nan):7.1f}'
                                       for y in sorted(ptot.index)))
    print('  Laredo %    ' + '  '.join(f'{y}: {100*lo.get(y, np.nan)/ptot.get(y, np.nan):7.1f}'
                                       for y in sorted(ptot.index)))

    # ---------------------------------------------------------------- corridor summary
    print('\n=== THE EL PASO CORRIDOR, $B ===')
    rows = []
    for y in YEARS:
        p = ex[(ex.code == PARTS) & (ex.flag == 'Re-export') & (ex.year == y) &
               (ex.place == EL_PASO_DISTRICT)]['value'].sum() / 1e9
        c = ex[(ex.code == CPUS) & (ex.flag == 'Re-export') & (ex.year == y) &
               (ex.place == EL_PASO_DISTRICT)]['value'].sum() / 1e9
        s = en[(en.year == y) & (en.place == EL_PASO_DISTRICT)]['value'].sum() / 1e9
        rows.append(dict(year=y, parts_out=p, cpus_out=c, components_out=p + c,
                         servers_in=s, ratio=s / (p + c) if (p + c) else np.nan))
    corr = pd.DataFrame(rows).set_index('year')
    print(corr.round(2).to_string())
    print('(2026 is January through March only)')

    # ---------------------------------------------------------------- figure
    # One panel, the corridor only. The Juarez-vs-Laredo time trend is carried by the
    # port table printed above and by the write-up, and does not need a second panel.
    yrs = [y for y in YEARS if y < 2026]
    fig, ax = plt.subplots(figsize=(12, 6.5))

    x = np.arange(len(yrs))
    w = 0.38
    parts = [corr.loc[y, 'parts_out'] for y in yrs]
    cpus = [corr.loc[y, 'cpus_out'] for y in yrs]
    servers = [corr.loc[y, 'servers_in'] for y in yrs]
    ax.bar(x - w / 2, parts, w, color='#4A90E2', edgecolor='black', linewidth=1.5,
           label='Parts re-exported south (8473300002)')
    ax.bar(x - w / 2, cpus, w, bottom=parts, color='#2E5090', edgecolor='black', linewidth=1.5,
           label='Processors re-exported south (854231)')
    ax.bar(x + w / 2, servers, w, color='#8B0000', edgecolor='black', linewidth=1.5,
           label='Servers imported north (8471500150)')
    headroom = max(servers) * 0.022
    for i, y in enumerate(yrs):
        out = parts[i] + cpus[i]
        ax.text(x[i] - w / 2, out + headroom, f'${out:.1f}B',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
        ax.text(x[i] + w / 2, servers[i] + headroom, f'${servers[i]:.1f}B',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
        # the ratio is the point of the panel: it barely moves while both bars triple
        ax.text(x[i], max(out, servers[i]) + headroom * 5.5, f'{servers[i]/out:.1f}x',
                ha='center', va='bottom', fontsize=13, fontweight='bold', color='#555555')
    ax.set_title('The El Paso corridor: components south, servers north',
                 fontsize=18, fontweight='bold', pad=18)
    ax.set_ylabel('$B, El Paso customs district', fontsize=16, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(yrs)
    ax.set_ylim(0, max(servers) * 1.32)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    for sp in ('right', 'top'):
        ax.spines[sp].set_visible(False)
    ax.spines['left'].set_linewidth(2)
    ax.spines['bottom'].set_linewidth(2)
    ax.tick_params(labelsize=13)
    for lab in ax.get_xticklabels():
        lab.set_fontweight('bold')
    ax.legend(fontsize=12, frameon=False, loc='upper left')

    plt.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(FIGDIR, f'mexico-border-crossings.{ext}'), bbox_inches='tight')
    plt.close(fig)
    print('\nwrote figures-mexico/mexico-border-crossings.png/.pdf')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='refetch even if cached')
    ap.add_argument('--key', default=None, help='Census API key')
    main(**vars(ap.parse_args()))
