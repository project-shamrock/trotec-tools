#!/usr/bin/env python3
"""Generate a cut test grid with progressive focal plane Z-offset per pass.

Each test cell stacks multiple same-location circles in different colors.
Each color maps to a Cut effect with a different ZOffset, so the focal
plane walks through the material depth across passes.

Grid: Frequency (rows) × Pass count (columns)
"""

import json
import sys
from pathlib import Path


# --- Configuration ---
FREQUENCIES = [1000, 3000, 5000]
PASS_COUNTS = [3, 4, 5]
SPEED = 0.5
POWER = 100
MATERIAL_THICKNESS = 5.75  # measured actual thickness

CIRCLE_RADIUS = 5  # mm
COL_SPACING = 35
ROW_SPACING = 30
MARGIN_X = 45
MARGIN_Y = 30

# Generate Z-offsets that walk the focal plane evenly through the material
def z_offsets_for_passes(n_passes, thickness=MATERIAL_THICKNESS):
    """Distribute focal points evenly through material depth."""
    if n_passes == 1:
        return [thickness / 2]
    step = thickness / (n_passes - 1)
    return [round(step * i, 2) for i in range(n_passes)]


# Generate unique colors - avoid blue (engrave) and stay visually distinct
def generate_colors(n):
    colors = []
    # Systematic: vary across hue space avoiding pure blue
    bases = [
        (0xFF, 0x00, 0x00),  # red
        (0xCC, 0x00, 0x00),  # dark red
        (0xFF, 0x33, 0x00),  # red-orange
        (0xCC, 0x33, 0x00),  # dark red-orange
        (0xFF, 0x66, 0x00),  # orange
        (0xCC, 0x66, 0x00),  # dark orange
        (0xFF, 0x99, 0x00),  # amber
        (0xCC, 0x99, 0x00),  # dark amber
        (0xFF, 0xCC, 0x00),  # yellow
        (0xCC, 0xCC, 0x00),  # dark yellow
        (0x99, 0x99, 0x00),  # olive
        (0x99, 0xCC, 0x00),  # yellow-green
        (0x66, 0x99, 0x00),  # green
        (0x33, 0x99, 0x00),  # dark green
        (0x00, 0x99, 0x33),  # teal
        (0x00, 0x99, 0x66),  # sea green
        (0x00, 0x99, 0x99),  # cyan
        (0x00, 0x66, 0x99),  # dark cyan
        (0x99, 0x00, 0x33),  # magenta
        (0x99, 0x00, 0x66),  # dark magenta
        (0xCC, 0x00, 0x66),  # hot pink
        (0xFF, 0x00, 0x66),  # rose
        (0xFF, 0x00, 0x99),  # pink
        (0xCC, 0x00, 0x99),  # dark pink
        (0x99, 0x00, 0x99),  # purple
        (0x66, 0x00, 0x99),  # deep purple
        (0x99, 0x33, 0x00),  # brown
        (0x66, 0x33, 0x00),  # dark brown
        (0x99, 0x66, 0x33),  # tan
        (0xCC, 0x33, 0x33),  # indian red
        (0x99, 0x33, 0x33),  # dark indian red
        (0xCC, 0x66, 0x33),  # peru
        (0xFF, 0x33, 0x33),  # salmon
        (0xFF, 0x66, 0x33),  # coral
        (0xFF, 0x99, 0x33),  # sandy
        (0xFF, 0xCC, 0x33),  # gold
    ]
    for i in range(n):
        r, g, b = bases[i % len(bases)]
        colors.append(f"{r:02X}{g:02X}{b:02X}")
    return colors


def generate_svg(output_path):
    """Generate the test SVG and return the effect definitions."""

    # Calculate all cells and their pass layers
    cells = []
    all_effects = []
    color_idx = 0

    for row_i, freq in enumerate(FREQUENCIES):
        for col_i, n_passes in enumerate(PASS_COUNTS):
            z_offsets = z_offsets_for_passes(n_passes)
            cell = {
                'row': row_i,
                'col': col_i,
                'freq': freq,
                'n_passes': n_passes,
                'z_offsets': z_offsets,
                'layers': [],
            }
            for pass_i, z in enumerate(z_offsets):
                cell['layers'].append({
                    'pass_num': pass_i + 1,
                    'z_offset': z,
                    'color_idx': color_idx,
                })
                all_effects.append({
                    'freq': freq,
                    'z_offset': z,
                    'color_idx': color_idx,
                    'pass_num': pass_i + 1,
                    'n_passes': n_passes,
                })
                color_idx += 1
            cells.append(cell)

    colors = generate_colors(color_idx)

    # Assign colors
    for eff in all_effects:
        eff['color'] = colors[eff['color_idx']]
    for cell in cells:
        for layer in cell['layers']:
            layer['color'] = colors[layer['color_idx']]

    # SVG dimensions
    n_cols = len(PASS_COUNTS)
    n_rows = len(FREQUENCIES)
    svg_w = MARGIN_X + n_cols * COL_SPACING + 20
    svg_h = MARGIN_Y + n_rows * ROW_SPACING + 20

    lines = []
    lines.append(f'<?xml version="1.0" encoding="utf-8" ?>')
    lines.append(f'<svg baseProfile="full" height="{svg_h}mm" version="1.1"')
    lines.append(f'     viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}mm"')
    lines.append(f'     xmlns="http://www.w3.org/2000/svg">')

    # Title
    lines.append(f'  <text fill="#0000FF" font-family="monospace" font-size="3" x="5" y="8">')
    lines.append(f'    FOCAL SWEEP CUT TEST - 6mm HDF - S{SPEED}% P{POWER}%</text>')
    lines.append(f'  <text fill="#0000FF" font-family="monospace" font-size="2" x="5" y="14">')
    lines.append(f'    Z walks through material depth on each pass</text>')

    # Column headers
    for col_i, n_passes in enumerate(PASS_COUNTS):
        x = MARGIN_X + col_i * COL_SPACING
        z_list = z_offsets_for_passes(n_passes)
        lines.append(f'  <text fill="#0000FF" font-family="monospace" font-size="2.2"'
                     f' x="{x - 5}" y="{MARGIN_Y - 12}">{n_passes} pass</text>')
        lines.append(f'  <text fill="#0000FF" font-family="monospace" font-size="1.5"'
                     f' x="{x - 8}" y="{MARGIN_Y - 7}">Z: {",".join(f"{z:.1f}" for z in z_list)}</text>')

    # Row headers and circles
    for row_i, freq in enumerate(FREQUENCIES):
        y_center = MARGIN_Y + row_i * ROW_SPACING + CIRCLE_RADIUS
        freq_label = f"{freq//1000}kHz" if freq >= 1000 else f"{freq}Hz"
        lines.append(f'  <text fill="#0000FF" font-family="monospace" font-size="2.2"'
                     f' x="5" y="{y_center + 1}">{freq_label}</text>')

    for cell in cells:
        cx = MARGIN_X + cell['col'] * COL_SPACING
        cy = MARGIN_Y + cell['row'] * ROW_SPACING + CIRCLE_RADIUS

        # Stack circles at same location, one per pass (different color = different Z)
        for layer in cell['layers']:
            color = layer['color']
            lines.append(f'  <circle cx="{cx}" cy="{cy}" r="{CIRCLE_RADIUS}"'
                        f' fill="none" stroke="#{color}" stroke-width="0.01"/>')

    lines.append('</svg>')

    svg_content = '\n'.join(lines)
    Path(output_path).write_text(svg_content)
    print(f"Generated {output_path}")
    print(f"  {len(cells)} test cells, {len(all_effects)} total effects")
    print(f"  SVG size: {svg_w}x{svg_h}mm")

    return all_effects, colors


def print_effect_table(effects, colors):
    """Print the effect configuration table."""
    print(f"\n{'Color':8s}  {'Freq':6s}  {'ZOff':6s}  {'Pass':4s}  {'of':3s}")
    print("-" * 35)
    for eff in effects:
        print(f"{colors[eff['color_idx']]:8s}  {eff['freq']:6d}  {eff['z_offset']:6.2f}  "
              f"{eff['pass_num']:4d}  {eff['n_passes']:3d}")


def generate_material_config(effects, colors):
    """Generate the material effects JSON for the Ruby API."""
    config = []
    for eff in effects:
        config.append({
            'color': colors[eff['color_idx']],
            'speed': SPEED,
            'power': POWER,
            'frequency': eff['freq'],
            'z_offset': eff['z_offset'],
            'passes': 1,  # each color = 1 pass at its own Z
        })
    return config


if __name__ == "__main__":
    output = "test-patterns/cut-focal-sweep.svg"
    effects, colors = generate_svg(output)
    print_effect_table(effects, colors)

    config = generate_material_config(effects, colors)
    config_path = "test-patterns/cut-focal-sweep-effects.json"
    Path(config_path).write_text(json.dumps(config, indent=2))
    print(f"\nEffect config written to {config_path}")
    print(f"Use this to configure the MDF material in Ruby.")
