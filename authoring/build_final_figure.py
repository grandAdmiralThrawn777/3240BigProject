"""Plot recorded C-model traces; no synthetic or interpolated measurements."""
from pathlib import Path
import argparse
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[2]
data = BASE/'implementation/Runs/tank-c59ibqve'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data', type=Path, default=data)
data = parser.parse_args().data
output = Path(__file__).parent
fig, axes = plt.subplots(2, 1, figsize=(6.6, 3.6), sharex=True)
for axis, name, label in zip(axes, ['T01_1', 'T02_1'], ['Normal demand', 'Demand changes at 200 s and 400 s']):
    with (data/(name+'.csv')).open() as stream:
        rows = list(csv.DictReader(stream))
    axis.plot([int(row['time_ms'])/1000 for row in rows],
              [int(row['level_bp'])/100 for row in rows], color='#284b63', lw=1.2)
    axis.axhline(30, color='0.5', linestyle='--', lw=0.7)
    axis.axhline(70, color='0.5', linestyle='--', lw=0.7)
    axis.set_ylim(20, 80)
    axis.set_ylabel('Level (%)', fontsize=9)
    axis.set_title(label, fontsize=10, loc='left')
    axis.tick_params(labelsize=8)
    axis.spines[['top', 'right']].set_visible(False)
axes[-1].set_xlabel('Model time (s)', fontsize=9)
fig.tight_layout(pad=0.8)
fig.savefig(output/'tank_results.pdf')
fig.savefig(output/'tank_results.png', dpi=160)
print('Created plot from recorded native C traces.')
