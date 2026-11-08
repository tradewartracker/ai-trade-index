# Figure Style Guide

Conventions used across matplotlib figures in this project. Port wholesale into other notebooks/projects.

## Color palette

| Role | Color | Use |
|---|---|---|
| Aggregate / total / reference | `black` | The "everything" line, neutral baseline |
| Primary highlight | `darkblue` or `#2E5090` | The series the figure is *about* (e.g. AI-Relevant) |
| Secondary highlight (contrast) | `#8B0000` (dark red) | The "concerning" or contrasting cut (e.g. Re-Exports, Not-AI) |
| Supporting third | `darkgreen` | When a fourth line is needed (e.g. Domestic) |
| Ranked groups (Top 1/2/3) | `#2E5090` → `#4A90E2` → `#7CB9E8` | Same-hue ramp, darkest = highest rank |

`alpha=0.7` on line series so overlaps stay legible.

## Typography

- **Title**: `fontsize=18-20, fontweight='bold', pad=20`
- **Axis labels**: `fontsize=16, fontweight='bold'`
- **Tick labels**: `fontsize=12-16` (12 when many ticks; 16 on simple time-series)
- **Value annotations on bars/points**: `fontsize=10-14, fontweight='bold'` — always bold, in the same color as the bar/line for line annotations
- **Bold x-tick labels** for categorical x-axes:
  ```python
  for label in ax.get_xticklabels():
      label.set_fontweight('bold')
  ```

## Figure sizes

| Chart type | `figsize` |
|---|---|
| Single time-series, paper figure | `(15, 9)` |
| Bar chart, 3–5 categories | `(10, 6)` to `(12, 6)` |
| Grouped bars, many categories | `(12, 6)` |

## Spines & grid

Strip top/right, thicken left/bottom — this is the consistent "clean" look:

```python
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['left'].set_linewidth(2)     # 3 on time series, 2 on bars
ax.spines['bottom'].set_linewidth(2)
ax.grid(axis='y', alpha=0.3, linestyle='--')   # only y grid, on bar charts
```

X-tick rotation: `rotation=25` for country names or year-months.

## Legend

```python
ax.legend(fontsize=12-16, frameon=False, loc='upper left')   # or 'upper right'
```

No frame, no shadow. Drop legend entries that are self-evident from position/x-ticks (e.g. don't label "Top 1/2/3 Country" if country names appear under each bar).

## Time-series indexing

Default to **annualized monthly index, 2023 = 100**, so monthly values are comparable to a 2023 annual baseline:

```python
base_2023 = series.loc["2023"].sum()
idx = 100 * (12 * series / base_2023)
```

End-of-line value annotation (no arrow), color-matched to the line:

```python
ax.annotate(f'{idx.iloc[-1]:.1f}',
            xy=(idx.index[-1], idx.iloc[-1]),
            xytext=(10, 0), textcoords='offset points',
            fontsize=14, fontweight='bold', color=line_color,
            va='center')
```

X-axis limit: pad the right edge so end-of-line labels don't clip
(e.g. `ax.set_xlim([start, last_date + a_few_days])`).

## Bar charts

- `edgecolor='black', linewidth=1.5` on every bar
- Value label above each bar, bold:
  ```python
  for bar in bars:
      h = bar.get_height()
      ax.text(bar.get_x() + bar.get_width()/2, h + 0.1,
              f'{h:.1f}%',  # or f'${h:.1f}B'
              ha='center', va='bottom', fontsize=11, fontweight='bold')
  ```
- Grouped bars: `width = 0.35` for 2 series, `0.22` for 3 series, positions at `x ± width/2` or `x - width, x, x + width`.

## Showing a sub-share without adding bars

When a bar already represents a total and you want to mark a sub-portion (e.g. re-exports inside total AI), use a hatched overlay rather than a second bar:

```python
ax.bar(bar_x, total_share, width, color=base_color, edgecolor='black', linewidth=1.5)
ax.bar(bar_x, sub_share,   width, color=base_color, edgecolor='black', linewidth=1.5, hatch='///')
```

The hatched fill sits on top of the bottom portion of the bar. Add ONE legend entry for the hatch and drop the redundant "group" entries:

```python
from matplotlib.patches import Patch
ax.legend(
    handles=[Patch(facecolor='white', edgecolor='black', hatch='///', label='Re-Exports')],
    fontsize=12, frameon=False, loc='upper right'
)
```

Bump `ylim` so the legend doesn't collide with in-plot annotations (`max_value * 1.40` is a good default).

## Saving

Always save **both PNG and PDF** with `bbox_inches='tight'`:

```python
plt.savefig(figfile + 'name.png', bbox_inches='tight')
plt.savefig(figfile + 'name.pdf', bbox_inches='tight')
plt.show()
```

PDF for paper inclusion, PNG for slides/quick previews.

## Reusable defaults snippet

Drop this at the top of a notebook to lock in the look:

```python
import matplotlib.pyplot as plt

plt.rcParams.update({
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'axes.linewidth':    2,
    'axes.labelweight':  'bold',
    'axes.titleweight':  'bold',
    'axes.titlesize':    18,
    'axes.labelsize':    16,
    'xtick.labelsize':   12,
    'ytick.labelsize':   12,
    'legend.frameon':    False,
    'legend.fontsize':   12,
    'grid.alpha':        0.3,
    'grid.linestyle':    '--',
    'savefig.bbox':      'tight',
})

PALETTE = {
    'aggregate':  'black',
    'primary':    'darkblue',     # or '#2E5090'
    'secondary':  '#8B0000',
    'tertiary':   'darkgreen',
    'rank1':      '#2E5090',
    'rank2':      '#4A90E2',
    'rank3':      '#7CB9E8',
}
```
