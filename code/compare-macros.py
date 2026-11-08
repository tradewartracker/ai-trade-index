"""Compare two LaTeX macro files such as paper/tables/ai-trade-results.tex.

usage: python code/compare-macros.py <reference.tex> <candidate.tex>

Reads \\def\\name{value} and \\newcommand{\\name}{value} lines from both files and prints the
macros whose values differ, with the percent change when both values are numeric, plus the
macros present in only one file. Used for the replication check (REPLICATION.md) and for
step 4 of the monthly refresh (UPDATE-PLAN.md), for example against the previous commit:

    git show HEAD:paper/tables/ai-trade-results.tex > previous.tex
    python code/compare-macros.py previous.tex paper/tables/ai-trade-results.tex
"""
import re
import sys


def parse(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    out = {}
    for m in re.finditer(r'\\def\\(\w+)\{([^}]*)\}', txt):
        out.setdefault(m.group(1), m.group(2).strip())
    for m in re.finditer(r'\\newcommand\{\\(\w+)\}\{([^}]*)\}', txt):
        out.setdefault(m.group(1), m.group(2).strip())
    return out


def num(s):
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return None


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    ref, cand = parse(sys.argv[1]), parse(sys.argv[2])
    names = sorted(set(ref) | set(cand))
    same = diff = one_side = 0
    rows = []
    for n in names:
        r, c = ref.get(n), cand.get(n)
        if r is None or c is None:
            one_side += 1
            rows.append((n, r if r is not None else '(absent)', c if c is not None else '(absent)', 'ONLY ONE SIDE'))
            continue
        if r == c:
            same += 1
            continue
        rn, cn = num(r), num(c)
        if rn is not None and cn is not None and rn != 0:
            flag = f'{100 * (cn - rn) / abs(rn):+.1f}%'
        else:
            flag = 'text'
        diff += 1
        rows.append((n, r, c, flag))

    print(f'macros: {len(names)} total | identical {same} | different {diff} | only one side {one_side}')
    if rows:
        print()
        w = max(len(r[0]) for r in rows)
        print(f'{"macro".ljust(w)}  {"reference".rjust(12)}  {"candidate".rjust(12)}  change')
        for n, r, c, f in rows:
            print(f'{n.ljust(w)}  {str(r).rjust(12)}  {str(c).rjust(12)}  {f}')


if __name__ == '__main__':
    main()
