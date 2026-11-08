"""Compare the PNG figures in two folders and write side-by-side composites for inspection.

usage: python code/compare-figures.py <reference_dir> <candidate_dir> <out_dir>

For each PNG in <reference_dir>, prints the share of pixels that differ noticeably from the
same-named file in <candidate_dir> (any RGB channel off by more than 40 of 255) and writes
<out_dir>/<name>.png with the reference on the left and the candidate on the right. Figures of
different size are resized to the reference before comparison and flagged. Needs Pillow and
numpy. A figure that replicates up to Census revisions comes back at about one percent or
less; see REPLICATION.md, section 5.
"""
import glob
import os
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError as e:
    sys.exit(f'{e}. This script needs numpy and Pillow (pip install numpy pillow).')


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    ref_dir, cand_dir, out_dir = sys.argv[1:4]
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for p in sorted(glob.glob(os.path.join(ref_dir, '*.png'))):
        name = os.path.basename(p)
        c = os.path.join(cand_dir, name)
        if not os.path.exists(c):
            rows.append((name, 'MISSING in candidate', ''))
            continue
        a = Image.open(p).convert('RGB')
        b = Image.open(c).convert('RGB')
        note = '' if a.size == b.size else f'size {a.size} vs {b.size}'
        b_cmp = b if a.size == b.size else b.resize(a.size)
        d = np.abs(np.asarray(a).astype(np.int16) - np.asarray(b_cmp).astype(np.int16)).max(axis=2)
        frac = float((d > 40).mean())
        rows.append((name, f'{100 * frac:5.1f}% pixels differ', note))
        comp = Image.new('RGB', (a.width + b.width + 20, max(a.height, b.height)), 'white')
        comp.paste(a, (0, 0))
        comp.paste(b, (a.width + 20, 0))
        comp.save(os.path.join(out_dir, name))

    if not rows:
        sys.exit(f'no PNG files in {ref_dir}')
    w = max(len(r[0]) for r in rows)
    for name, verdict, note in rows:
        print(f'{name.ljust(w)}  {verdict}  {note}')
    print(f'\ncomposites written to {out_dir}')


if __name__ == '__main__':
    main()
