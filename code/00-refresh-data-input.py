"""
Refresh data-input/ from the canonical trade-data repo (C:/heroku/trade-data).

Run from anywhere:   python code/00-refresh-data-input.py
Then run the paper pipeline (code/run-paper.ipynb, or notebooks 06 -> 11 in order).

What it does
------------
1. Moves the current data-input parquets into data-input/vintage-<YYYY-MM>/ where
   <YYYY-MM> is the last month in the current TOTALdata-current.parquet. Refuses to
   overwrite anything already in that folder (a failed run must not clobber a backup).
2. Imports: copies the legacy-schema products that trade-data already builds
   (data/products/tri-imports-hs10/: TOTAL + 30 countries + EU 0003 + USMCA 0020)
   into TOTALdata-current.parquet and ALL-data-current.parquet.
3. Exports: streams data/exports/ALL-data-current.parquet (new schema) into the four
   legacy-schema files the notebooks read: TOTALexports-combined.parquet,
   All-country-exports.parquet, and the two *-DF.parquet re-export splits
   (export_type = Total / Domestic / Re-Exports from the df grain: '-', '1', '2').
   Country universe: the 31 entities used in the published paper (30 countries + EU).
4. Verifies row counts, time range, and that no (entity, month, HS10) key repeats.

Legacy schema (all columns string, time as 'YYYY-MM'):
  imports: CTY_NAME, CON_VAL_MO, CAL_DUT_MO, I_COMMODITY, I_COMMODITY_SDESC, time, COMM_LVL[, CTY_CODE]
  exports: CTY_NAME, ALL_VAL_MO, E_COMMODITY, E_COMMODITY_SDESC, COMM_LVL, time[, CTY_CODE][, export_type]

pyarrow's strftime needs a timezone database that is missing on this Windows box, so the
month string is built from year() and month() instead.
"""
import glob
import os
import shutil
import sys
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DI = os.path.join(REPO, 'data-input')
TRADE_DATA = 'C:/heroku/trade-data'
IMPORT_PRODUCTS = f'{TRADE_DATA}/data/products/tri-imports-hs10'
EXPORT_BASE = f'{TRADE_DATA}/data/exports/ALL-data-current.parquet'

# 31-entity export universe of the published paper (30 countries + EU 0003)
LEGACY_EXPORT_CODES = ['0003', '1220', '2010', '3010', '3330', '3370', '3510', '4120', '4190', '4210',
                       '4231', '4279', '4280', '4419', '4700', '4759', '4890', '5081', '5170', '5200',
                       '5330', '5490', '5520', '5570', '5590', '5700', '5800', '5820', '5830', '5880', '6021']
DF_START = '2022-01'   # the re-export split files start here, as the legacy ones did

IMPORT_FILES = ['TOTALdata-current.parquet', 'ALL-data-current.parquet']
EXPORT_FILES = ['TOTALexports-combined.parquet', 'All-country-exports.parquet',
                'TOTALexports-combined-DF.parquet', 'All-country-exports-DF.parquet']


def month_string(ts):
    """timestamp array -> 'YYYY-MM' string array without needing a tz database."""
    y = pc.cast(pc.year(ts), pa.string())
    m = pc.utf8_lpad(pc.cast(pc.month(ts), pa.string()), 2, '0')
    return pc.binary_join_element_wise(y, m, '-')


def current_vintage_label():
    p = os.path.join(DI, 'TOTALdata-current.parquet')
    if not os.path.exists(p):
        return None
    t = pq.read_table(p, columns=['time'])
    return pc.max(t['time']).as_py()


def stash_current_files():
    label = current_vintage_label()
    if label is None:
        print('no existing TOTALdata-current.parquet; nothing to stash')
        return
    vin = os.path.join(DI, f'vintage-{label}')
    os.makedirs(vin, exist_ok=True)
    for f in IMPORT_FILES + EXPORT_FILES:
        src = os.path.join(DI, f)
        if not os.path.exists(src):
            continue
        dst = os.path.join(vin, f)
        if os.path.exists(dst):
            sys.exit(f'refusing to overwrite existing backup {dst}; move it aside first')
        shutil.move(src, dst)
        print(f'stashed {f} -> vintage-{label}/')


def build_imports():
    t0 = time.time()
    shutil.copy2(f'{IMPORT_PRODUCTS}/TOTALdata-current.parquet', os.path.join(DI, 'TOTALdata-current.parquet'))
    cols = ['CTY_NAME', 'CON_VAL_MO', 'CAL_DUT_MO', 'I_COMMODITY', 'I_COMMODITY_SDESC', 'time', 'COMM_LVL', 'CTY_CODE']
    schema = pa.schema([(c, pa.string()) for c in cols])
    files = sorted(glob.glob(f'{IMPORT_PRODUCTS}/*data-current.parquet'))
    if len(files) != 33:
        sys.exit(f'expected 33 import product files, found {len(files)}')
    w = pq.ParquetWriter(os.path.join(DI, 'ALL-data-current.parquet'), schema)
    n, maxdup, tmax = 0, 0, ''
    for f in files:
        t = pq.read_table(f)
        if 'CTY_CODE' not in t.column_names:          # the TOTAL file carries no code
            t = t.append_column('CTY_CODE', pa.array(['TOTAL'] * t.num_rows, pa.string()))
        t = t.select(cols).cast(schema)
        g = t.select(['time', 'I_COMMODITY']).group_by(['time', 'I_COMMODITY']).aggregate([([], 'count_all')])
        maxdup = max(maxdup, pc.max(g['count_all']).as_py())
        tmax = max(tmax, pc.max(t['time']).as_py())
        w.write_table(t)
        n += t.num_rows
    w.close()
    print(f'imports: ALL-data-current.parquet {n:,} rows, through {tmax}, max duplicate key = {maxdup}, {time.time()-t0:.0f}s')
    if maxdup != 1:
        sys.exit('duplicate (entity, month, HS10) keys in imports; aborting')


def build_exports():
    t0 = time.time()
    base = ['CTY_NAME', 'ALL_VAL_MO', 'E_COMMODITY', 'E_COMMODITY_SDESC', 'COMM_LVL', 'time']
    schemas = {
        'TOTALexports-combined.parquet':    pa.schema([(c, pa.string()) for c in base]),
        'All-country-exports.parquet':      pa.schema([(c, pa.string()) for c in base + ['CTY_CODE']]),
        'TOTALexports-combined-DF.parquet': pa.schema([(c, pa.string()) for c in base + ['export_type']]),
        'All-country-exports-DF.parquet':   pa.schema([(c, pa.string()) for c in base + ['CTY_CODE', 'export_type']]),
    }
    writers = {k: pq.ParquetWriter(os.path.join(DI, k), s) for k, s in schemas.items()}
    buf = {k: [] for k in writers}
    bufn = {k: 0 for k in writers}
    total = {k: 0 for k in writers}

    def flush(k):
        if buf[k]:
            writers[k].write_table(pa.concat_tables(buf[k]))
            total[k] += bufn[k]
            buf[k], bufn[k] = [], 0

    def push(k, t):
        if t.num_rows:
            buf[k].append(t.select(schemas[k].names))
            bufn[k] += t.num_rows
            if bufn[k] >= 1_500_000:
                flush(k)

    et_keys = pa.array(['-', '1', '2'])
    et_vals = pa.array(['Total Exports', 'Domestic Exports', 'Re-Exports'])
    d = ds.dataset(EXPORT_BASE)
    filt = ds.field('cty_code').isin(LEGACY_EXPORT_CODES) | (ds.field('entity_kind') == 'total')
    scanner = d.scanner(columns=['cty_code', 'cty_name', 'entity_kind', 'hs10', 'desc_short', 'comm_lvl', 'df', 'value', 'time'],
                        filter=filt, batch_size=250_000)
    for b in scanner.to_batches():
        if not b.num_rows:
            continue
        t = pa.Table.from_batches([b])
        out = pa.table({
            'CTY_NAME': t['cty_name'],
            'ALL_VAL_MO': pc.cast(t['value'], pa.string()),
            'E_COMMODITY': t['hs10'],
            'E_COMMODITY_SDESC': t['desc_short'],
            'COMM_LVL': t['comm_lvl'],
            'time': month_string(t['time']),
            'CTY_CODE': t['cty_code'],
            'export_type': pc.take(et_vals, pc.index_in(t['df'], value_set=et_keys)),
        })
        is_tot = pc.equal(t['entity_kind'], 'total')
        is_dash = pc.equal(t['df'], '-')
        in_df_window = pc.greater_equal(out['time'], DF_START)
        push('TOTALexports-combined.parquet',    out.filter(pc.and_(is_tot, is_dash)))
        push('All-country-exports.parquet',      out.filter(pc.and_(pc.invert(is_tot), is_dash)))
        push('TOTALexports-combined-DF.parquet', out.filter(pc.and_(is_tot, in_df_window)))
        push('All-country-exports-DF.parquet',   out.filter(pc.and_(pc.invert(is_tot), in_df_window)))
    for k in writers:
        flush(k)
        writers[k].close()
    print(f'exports: {time.time()-t0:.0f}s; rows written: ' + ', '.join(f'{k} {v:,}' for k, v in total.items()))

    tt = pq.read_table(os.path.join(DI, 'TOTALexports-combined.parquet'), columns=['time', 'E_COMMODITY'])
    g = tt.group_by(['time', 'E_COMMODITY']).aggregate([([], 'count_all')])
    maxdup = pc.max(g['count_all']).as_py()
    print(f'exports: TOTAL through {pc.max(tt["time"]).as_py()}, max duplicate key = {maxdup}')
    if maxdup != 1:
        sys.exit('duplicate (month, HS10) keys in TOTAL exports; aborting')


if __name__ == '__main__':
    for p in (IMPORT_PRODUCTS, EXPORT_BASE):
        if not os.path.exists(p):
            sys.exit(f'missing upstream input: {p}')
    stash_current_files()
    build_imports()
    build_exports()
    print('done. Next: run code/run-paper.ipynb (notebooks 06 -> 11).')
