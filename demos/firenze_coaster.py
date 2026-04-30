#!/usr/bin/env python3
"""Generate a Firenze-themed coaster for laser cutter demo.

Circular coaster with:
  - Red (#FF0000) cut outline
  - Black (#000000) engraved Ponte Vecchio silhouette + text

The Ponte Vecchio is constructed from architectural reference:
  - Three segmental arches (center arch largest)
  - Shops overhanging on both sides with varied rooflines
  - Vasari Corridor running along the top (east side, taller)
  - Distinctive backshop extensions hanging over the river
  - Stone piers with cutwaters
"""

import math
import svgwrite

# --- Dimensions (mm) ---
DIAMETER = 90.0
RADIUS = DIAMETER / 2.0
MARGIN = 5.0
CX = MARGIN + RADIUS
CY = MARGIN + RADIUS

CUT_COLOR = "#FF0000"
ENG = "#000000"
SW = 0.01


def draw_ponte_vecchio(dwg, cx, cy):
    """Draw a detailed Ponte Vecchio silhouette centered at (cx, cy).

    The bridge is drawn as filled black shapes for engraving.
    Architectural elements from east (left) to west (right):
    - The bridge has 3 arches: two flanking (smaller) and one center (larger)
    - Shops line the bridge deck with backshops overhanging the river
    - The Vasari Corridor runs along the upstream (south/top) side
    - Tower-like structures at each end
    """
    # Coordinate system: bridge centered at cx, water level at cy + 6
    wl = cy + 6  # water line (top of arches)
    deck = wl - 2.5  # bridge deck level (road surface)

    # === ARCHES ===
    # Three arches: left (smaller), center (larger), right (smaller)
    # Actual proportions: center span ~30m, side spans ~27m each
    arch_data = [
        # (center_x_offset, half_span, rise)
        (-15.5, 6.5, 7),    # left arch
        (0, 7.5, 8.5),      # center arch (largest)
        (15.5, 6.5, 7),     # right arch
    ]

    for ax_off, half_span, rise in arch_data:
        acx = cx + ax_off
        x1 = acx - half_span
        x2 = acx + half_span
        # Draw arch as filled area below deck
        # Path: deck left -> arch curve -> deck right -> close along deck
        d = f"M {x1:.1f},{wl:.1f}"
        d += f" A {half_span:.1f},{rise:.1f} 0 0 1 {x2:.1f},{wl:.1f}"
        dwg.add(dwg.path(d=d, fill="none", stroke=ENG, stroke_width=0.6))

    # === PIERS ===
    # Two piers between arches, with triangular cutwaters
    pier_w = 3.0
    pier_depth = 10.0
    for px_off in [-8, 8]:
        px = cx + px_off
        # Pier body
        dwg.add(dwg.rect(
            insert=(px - pier_w/2, wl),
            size=(pier_w, pier_depth),
            fill=ENG, stroke="none",
        ))
        # Cutwater (triangular, pointing downstream)
        cw = f"M {px:.1f},{wl + pier_depth:.1f}"
        cw += f" L {px - pier_w/2 - 0.5:.1f},{wl + pier_depth:.1f}"
        cw += f" L {px:.1f},{wl + pier_depth + 2.5:.1f}"
        cw += f" L {px + pier_w/2 + 0.5:.1f},{wl + pier_depth:.1f} Z"
        dwg.add(dwg.path(d=cw, fill=ENG, stroke="none"))

    # === BRIDGE DECK ===
    deck_x1 = cx - 26
    deck_x2 = cx + 26
    deck_h = 2.5
    dwg.add(dwg.rect(
        insert=(deck_x1, deck), size=(deck_x2 - deck_x1, deck_h),
        fill=ENG, stroke="none",
    ))

    # === ABUTMENTS (bridge ends) ===
    abut_h = 14
    # Left abutment
    dwg.add(dwg.rect(
        insert=(deck_x1 - 3, deck - abut_h + 3),
        size=(5, abut_h),
        fill=ENG, stroke="none",
    ))
    # Right abutment
    dwg.add(dwg.rect(
        insert=(deck_x2 - 2, deck - abut_h + 3),
        size=(5, abut_h),
        fill=ENG, stroke="none",
    ))

    # === SHOPS AND BUILDINGS ===
    # The shops line both sides of the road. We show the downstream elevation.
    # Buildings have varied heights with the Vasari Corridor on top.
    # Left bank buildings -> bridge shops -> right bank buildings

    shop_top = deck  # shops sit on the deck

    # Building data: (x_left_offset, width, height_above_deck)
    # Arranged left to right across the bridge
    buildings = [
        # Left bank approach
        (-27, 4, 10),
        (-23, 4, 12),
        # Left bridge shops
        (-19, 3.5, 7),
        (-15.5, 3, 8),
        (-12.5, 3, 6.5),
        # Left side approaching center
        (-9.5, 3, 9),
        (-6.5, 3.5, 7),
        # Center opening (Vasari corridor gap - open loggia)
        # Skip -3 to +3 for the open area
        # Right side from center
        (3, 3.5, 7.5),
        (6.5, 3, 9),
        # Right bridge shops
        (9.5, 3, 7),
        (12.5, 3, 8.5),
        (15.5, 3.5, 6.5),
        # Right bank approach
        (19, 4, 11),
        (23, 4, 13),
    ]

    for bx_off, bw, bh in buildings:
        bx = cx + bx_off
        dwg.add(dwg.rect(
            insert=(bx, shop_top - bh),
            size=(bw, bh),
            fill=ENG, stroke="none",
        ))

    # === VASARI CORRIDOR ===
    # Runs along the top, especially prominent on the left (east) side
    # It's a continuous elevated passage above the shops
    vc_y = deck - 13
    vc_h = 3
    # Left section
    dwg.add(dwg.rect(
        insert=(cx - 23, vc_y), size=(20, vc_h),
        fill=ENG, stroke="none",
    ))
    # Right section (slightly lower)
    dwg.add(dwg.rect(
        insert=(cx + 3, vc_y + 1), size=(20, vc_h),
        fill=ENG, stroke="none",
    ))

    # Vasari corridor windows (small openings)
    win_w = 1.2
    win_h = 1.5
    for wx in range(-21, -4, 3):
        dwg.add(dwg.rect(
            insert=(cx + wx, vc_y + 0.8),
            size=(win_w, win_h),
            fill="white", stroke="none",
        ))
    for wx in range(5, 21, 3):
        dwg.add(dwg.rect(
            insert=(cx + wx, vc_y + 1.8),
            size=(win_w, win_h),
            fill="white", stroke="none",
        ))

    # === BACKSHOPS (overhanging extensions) ===
    # The iconic overhanging shops supported by brackets (sporto)
    for bx_off in [-18, -14, -10, -6, 4, 8, 12, 16]:
        bx = cx + bx_off
        bw = 2.5
        bh = 4
        # Overhanging box
        dwg.add(dwg.rect(
            insert=(bx, deck),
            size=(bw, bh),
            fill=ENG, stroke="none",
        ))
        # Support bracket (diagonal line)
        d = f"M {bx:.1f},{deck + bh:.1f} L {bx + bw/2:.1f},{deck:.1f}"
        dwg.add(dwg.path(d=d, fill="none", stroke=ENG, stroke_width=0.3))
        d2 = f"M {bx + bw:.1f},{deck + bh:.1f} L {bx + bw/2:.1f},{deck:.1f}"
        dwg.add(dwg.path(d=d2, fill="none", stroke=ENG, stroke_width=0.3))

    # === CENTER LOGGIA ===
    # The open area in the center of the bridge (three arched openings)
    loggia_y = deck - 8
    for lx_off in [-2, 0, 2]:
        lx = cx + lx_off * 1.5
        col_w = 0.4
        # Columns
        dwg.add(dwg.rect(
            insert=(lx - col_w/2, loggia_y), size=(col_w, 8),
            fill=ENG, stroke="none",
        ))
    # Loggia lintel
    dwg.add(dwg.rect(
        insert=(cx - 3.5, loggia_y - 0.8), size=(7, 1),
        fill=ENG, stroke="none",
    ))
    # Small arches in the loggia
    for lx_off in [-1.5, 0, 1.5]:
        x1 = cx + lx_off - 0.6
        x2 = cx + lx_off + 0.6
        d = f"M {x1:.2f},{loggia_y:.2f} A 0.6,0.8 0 0 1 {x2:.2f},{loggia_y:.2f}"
        dwg.add(dwg.path(d=d, fill="none", stroke=ENG, stroke_width=0.3))

    # === ROOFLINE DETAILS ===
    # Add varied rooftops (triangular pediments on some buildings)
    roof_data = [
        (-21, 4, 2),   # left bank
        (-7.5, 3, 1.5),
        (5, 3, 1.5),
        (21, 4, 2),    # right bank
    ]
    for rx_off, rw, rh in roof_data:
        rx = cx + rx_off
        bldg_top = None
        for bx_off, bw, bh in buildings:
            if abs(bx_off - rx_off) < 2:
                bldg_top = deck - bh
                break
        if bldg_top is None:
            continue
        d = f"M {rx:.1f},{bldg_top:.1f} L {rx + rw/2:.1f},{bldg_top - rh:.1f} L {rx + rw:.1f},{bldg_top:.1f} Z"
        dwg.add(dwg.path(d=d, fill=ENG, stroke="none"))

    # === WATER REFLECTIONS ===
    for wy_off in [2, 4.5, 7]:
        wy = wl + wy_off
        d = f"M {cx - 28:.1f},{wy:.1f}"
        for i in range(-27, 28):
            x = cx + i
            y = wy + math.sin(i * 0.7) * 0.5
            d += f" L {x:.2f},{y:.2f}"
        dwg.add(dwg.path(d=d, fill="none", stroke=ENG, stroke_width=0.2))

    # === RIVERBANKS ===
    # Embankment walls on each side
    dwg.add(dwg.path(
        d=f"M {cx - 26:.1f},{wl:.1f} L {cx - 32:.1f},{wl + 1:.1f} L {cx - 32:.1f},{wl + 12:.1f}",
        fill="none", stroke=ENG, stroke_width=0.5,
    ))
    dwg.add(dwg.path(
        d=f"M {cx + 26:.1f},{wl:.1f} L {cx + 32:.1f},{wl + 1:.1f} L {cx + 32:.1f},{wl + 12:.1f}",
        fill="none", stroke=ENG, stroke_width=0.5,
    ))


def arc_text(dwg, text, cx, cy, r, start_deg, span_deg, font_size=5,
             top=True):
    """Place text along a circular arc.

    top=True: text reads left-to-right along the top of the circle.
    top=False: text reads left-to-right along the bottom of the circle.
    """
    n = len(text)
    for i, ch in enumerate(text):
        # Position along arc
        if top:
            angle_deg = start_deg + (i + 0.5) * span_deg / n
        else:
            # Bottom: go right-to-left in angle so text reads L-to-R
            angle_deg = start_deg - (i + 0.5) * span_deg / n

        angle = math.radians(angle_deg)
        tx = cx + r * math.cos(angle)
        ty = cy + r * math.sin(angle)

        if top:
            rot = angle_deg + 90
        else:
            rot = angle_deg - 90

        dwg.add(dwg.text(
            ch, insert=(tx, ty),
            font_size=str(font_size), font_family="serif",
            font_weight="bold",
            fill=ENG, stroke="none",
            text_anchor="middle", dominant_baseline="central",
            transform=f"rotate({rot:.1f},{tx:.2f},{ty:.2f})",
        ))


def generate():
    size = DIAMETER + 2 * MARGIN
    dwg = svgwrite.Drawing(
        "demos/firenze_coaster.svg",
        size=(f"{size}mm", f"{size}mm"),
        viewBox=f"0 0 {size} {size}",
    )

    # Cut outline - red circle
    dwg.add(dwg.circle(
        center=(CX, CY), r=RADIUS,
        stroke=CUT_COLOR, stroke_width=SW, fill="none",
    ))

    # Decorative rings - engraved
    dwg.add(dwg.circle(
        center=(CX, CY), r=RADIUS - 3,
        stroke=ENG, stroke_width=0.3, fill="none",
    ))
    dwg.add(dwg.circle(
        center=(CX, CY), r=RADIUS - 4,
        stroke=ENG, stroke_width=0.15, fill="none",
    ))

    # Ponte Vecchio
    draw_ponte_vecchio(dwg, CX, CY)

    # "GOOD STUDIO" along top arc (reads left to right)
    arc_text(dwg, "GOOD STUDIO", CX, CY, RADIUS - 7.5,
             start_deg=230, span_deg=80, font_size=5, top=True)

    # "FIRENZE" along bottom arc (reads left to right)
    arc_text(dwg, "FIRENZE", CX, CY, RADIUS - 7.5,
             start_deg=130, span_deg=60, font_size=5, top=False)

    # Decorative dots as separators (between the two text arcs)
    for angle_deg in [175, 5]:
        angle = math.radians(angle_deg)
        dx = CX + (RADIUS - 7.5) * math.cos(angle)
        dy = CY + (RADIUS - 7.5) * math.sin(angle)
        dwg.add(dwg.circle(center=(dx, dy), r=0.8,
                            fill=ENG, stroke="none"))

    dwg.save()
    print(f"Generated demos/firenze_coaster.svg")
    print(f"  {DIAMETER}mm diameter coaster")
    print(f"  Red circle = cut, black = engrave")


if __name__ == "__main__":
    generate()
