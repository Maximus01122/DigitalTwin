"""
plot_compare.py — Compare up to three CSV thermal runs on the same chart.

Usage:
    python plot_compare.py <csv1> <csv2> [csv3] --col1 <cols...> --col2 <cols...> [--col3 <cols...>]
                          [--x <col>] [--labels <l1> <l2> [l3]]

Examples:
    # Two files
    python plot_compare.py run_a.csv run_b.csv --col1 t_actual --col2 t_actual

    # Three files
    python plot_compare.py run_a.csv run_b.csv run_c.csv --col1 t_actual --col2 t_actual --col3 t_actual

    # Custom labels
    python plot_compare.py run_a.csv run_b.csv run_c.csv \\
        --col1 t_actual --col2 t_actual --col3 t_actual \\
        --labels "Motor ON" "Motor OFF" "No Load"
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# --- Argument Parsing ---
parser = argparse.ArgumentParser(
    description="Plot columns from two or three CSV files on the same chart."
)
parser.add_argument("csv1", help="Path to the first CSV file")
parser.add_argument("csv2", help="Path to the second CSV file")
parser.add_argument("csv3", nargs="?", default=None, help="Path to the optional third CSV file")
parser.add_argument("csv4", nargs="?", default=None, help="Path to the optional fourth CSV file")
parser.add_argument("--col1", nargs="+", required=True, help="Column(s) to plot from CSV1")
parser.add_argument("--col2", nargs="+", required=True, help="Column(s) to plot from CSV2")
parser.add_argument("--col3", nargs="+", default=None,  help="Column(s) to plot from CSV3 (required if csv3 provided)")
parser.add_argument("--col4", nargs="+", default=None,  help="Column(s) to plot from CSV4 (required if csv4 provided)")
parser.add_argument("--x", default="seconds", help="X-axis column name (default: 'seconds')")
parser.add_argument("--labels", nargs="+", default=None, help="Custom legend labels for each file")
args = parser.parse_args()

# --- Validate csv3/col3 and csv4/col4 combos ---
if args.csv3 and not args.col3:
    print("ERROR: csv3 was provided but --col3 is missing.")
    sys.exit(1)
if args.col3 and not args.csv3:
    print("ERROR: --col3 was provided but csv3 path is missing.")
    sys.exit(1)
if args.csv4 and not args.col4:
    print("ERROR: csv4 was provided but --col4 is missing.")
    sys.exit(1)
if args.col4 and not args.csv4:
    print("ERROR: --col4 was provided but csv4 path is missing.")
    sys.exit(1)

# --- Load Data ---
def load_csv(path):
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    return pd.read_csv(path)

df1 = load_csv(args.csv1)
df2 = load_csv(args.csv2)
df3 = load_csv(args.csv3) if args.csv3 else None
df4 = load_csv(args.csv4) if args.csv4 else None
def filt(a): return a[a['seconds'] <= 8000]
df1 = filt(df1)
df2 = filt(df2)
if df3 is not None:
    df3 = filt(df3)
if df4 is not None:
    df4 = filt(df4)
# --- Labels ---
default_labels = [os.path.basename(args.csv1), os.path.basename(args.csv2)]
if args.csv3:
    default_labels.append(os.path.basename(args.csv3))
if args.csv4:
    default_labels.append(os.path.basename(args.csv4))
labels = args.labels if args.labels else default_labels

# --- Validate columns ---
def validate(df, cols, path):
    for col in cols + [args.x]:
        if col not in df.columns:
            print(f"ERROR: Column '{col}' not found in {path}")
            print(f"       Available columns: {list(df.columns)}")
            sys.exit(1)

validate(df1, args.col1, args.csv1)
validate(df2, args.col2, args.csv2)
if df3 is not None:
    validate(df3, args.col3, args.csv3)
if df4 is not None:
    validate(df4, args.col4, args.csv4)

# --- Plot ---
fig, ax = plt.subplots(figsize=(12, 6))
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

FILE_COLORS = ["#e63946", "#1d7cb8", "#e67e22", "#2ecc71"]  # red, blue, orange, green

files = [(df1, args.col1, labels[0]), (df2, args.col2, labels[1])]
if df3 is not None:
    files.append((df3, args.col3, labels[2] if len(labels) > 2 else os.path.basename(args.csv3)))
if df4 is not None:
    files.append((df4, args.col4, labels[3] if len(labels) > 3 else os.path.basename(args.csv4)))

for i, (df, cols, label) in enumerate(files):
    color = FILE_COLORS[i]
    for col in cols:
        ax.plot(
            df[args.x].to_numpy(), df[col].to_numpy(),
            color=color, linewidth=2, linestyle="-",
            label=f"{label} — {col}"
        )

# --- Styling ---
ax.set_xlabel(args.x, color="black", fontsize=12)
ax.set_ylabel("Value", color="black", fontsize=12)
all_cols = args.col1 + args.col2 + (args.col3 or []) + (args.col4 or [])
ax.tick_params(colors="black")
ax.spines["bottom"].set_color("#aaaaaa")
ax.spines["left"].set_color("#aaaaaa")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(facecolor="white", edgecolor="#cccccc", labelcolor="black", fontsize=10)
ax.grid(color="#dddddd", linestyle="--", linewidth=0.7, alpha=0.9)

plt.tight_layout()
plt.show()
