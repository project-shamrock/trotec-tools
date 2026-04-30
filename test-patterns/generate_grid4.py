#!/usr/bin/env python3
"""Generate Grid 4: Frequency × Passes test pattern.

Grid: Frequency (rows: 4kHz, 5kHz, 6kHz) × Passes (columns: 1, 2, 3)
Fixed: Speed 0.5%, Power 100%, ZOffset 0

Each cell is one circle with a unique color. One Cut effect per color,
with the cell's frequency and pass count.
"""

import json
from pathlib import Path

# --- Configuration ---
FREQUENCIES = [1000, 3000, 5000]
PASS_COUNTS = [1, 2, 3]
SPEEDS = {1: 0.5, 2: 0.7, 3: 1.0}  # speed per pass count
POWER = 100

CIRCLE_RADIUS = 5  # mm
COL_SPACING = 30
ROW_SPACING = 25
MARGIN_X = 35
MARGIN_Y = 25

# Ruby predefined colors — must match material effect layers exactly
# Avoid 0000FF (blue=engrave) and 000000 (black=engrave)
COLORS = [
    "FF0000", "00FFFF", "00FF00",  # 1kHz: 1p, 2p, 3p
    "FF6600", "FFFF00", "FF00FF",  # 3kHz: 1p, 2p, 3p
    "336699", "009933", "9900CC",  # 5kHz: 1p, 2p, 3p
]


def generate():
    cells = []
    effects = []
    idx = 0

    for row_i, freq in enumerate(FREQUENCIES):
        for col_i, passes in enumerate(PASS_COUNTS):
            color = COLORS[idx]
            cells.append({
                'row': row_i, 'col': col_i,
                'freq': freq, 'passes': passes, 'color': color,
            })
            effects.append({
                'color': color,
                'speed': SPEEDS[passes],
                'power': POWER,
                'frequency': freq,
                'z_offset': 0,
                'passes': passes,
            })
            idx += 1

    # SVG
    n_cols = len(PASS_COUNTS)
    n_rows = len(FREQUENCIES)
    svg_w = MARGIN_X + n_cols * COL_SPACING + 15
    svg_h = MARGIN_Y + n_rows * ROW_SPACING + 15

    lines = []
    lines.append(f'<?xml version="1.0" encoding="utf-8" ?>')
    lines.append(f'<svg baseProfile="full" height="{svg_h}mm" version="1.1"')
    lines.append(f'     viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}mm"')
    lines.append(f'     xmlns="http://www.w3.org/2000/svg">')

    # Title — use black for text (engrave is disabled, black won't cut)
    lines.append(f'  <text fill="#000000" font-family="monospace" font-size="3" x="5" y="8">')
    lines.append(f'    GRID 4: FREQ x PASSES - P{POWER}% Z0</text>')

    # Column headers
    for col_i, passes in enumerate(PASS_COUNTS):
        x = MARGIN_X + col_i * COL_SPACING
        lines.append(f'  <text fill="#000000" font-family="monospace" font-size="2.2"'
                     f' x="{x - 3}" y="{MARGIN_Y - 5}">{passes} pass</text>')

    # Row headers
    for row_i, freq in enumerate(FREQUENCIES):
        y = MARGIN_Y + row_i * ROW_SPACING + CIRCLE_RADIUS
        lines.append(f'  <text fill="#000000" font-family="monospace" font-size="2.2"'
                     f' x="5" y="{y + 1}">{freq // 1000}kHz</text>')

    # Circles
    for cell in cells:
        cx = MARGIN_X + cell['col'] * COL_SPACING
        cy = MARGIN_Y + cell['row'] * ROW_SPACING + CIRCLE_RADIUS
        lines.append(f'  <circle cx="{cx}" cy="{cy}" r="{CIRCLE_RADIUS}"'
                     f' fill="none" stroke="#{cell["color"]}" stroke-width="0.01"/>')

    lines.append('</svg>')

    svg_path = "test-patterns/cut-grid-test4.svg"
    Path(svg_path).write_text('\n'.join(lines))

    config_path = "test-patterns/cut-grid-test4-effects.json"
    Path(config_path).write_text(json.dumps(effects, indent=2))

    print(f"Generated {svg_path}")
    print(f"  {len(cells)} test cells, {len(effects)} effects")
    print(f"  SVG size: {svg_w}x{svg_h}mm")
    print(f"\nEffect config written to {config_path}")

    # Print table
    print(f"\n{'Color':8s}  {'Freq':6s}  {'Passes':6s}")
    print("-" * 25)
    for eff in effects:
        print(f"{eff['color']:8s}  {eff['frequency']:6d}  {eff['passes']:6d}")


if __name__ == "__main__":
    generate()
