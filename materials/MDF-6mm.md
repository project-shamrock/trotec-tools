# MDF 6mm — Cut Profile for Trotec Q400_RF

**Machine**: Trotec Q400_RF (serial Q42-3066, 60W CeramiCore RF CO2)
**Date tested**: 2026-04-29 (updated from 2026-04-28)
**Stock**: 6mm HDF (Italian-sourced, confirmed ~861 kg/m³ — see density measurement below)

## Current Best Settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| Power | 100% | Maximum required for 6mm |
| Speed | 0.3% | Conservative; 0.4% also works |
| Passes | 1 | Single pass with manual midplane focus |
| Frequency | 1,000 Hz | Cleanest cut edges per Trotec recommendation |
| ZOffset | 0 mm | Focus set manually (see focusing procedure below) |
| AirAssist | On | Standard |
| PowerCorrection | 7% | Default |
| Cut color | Red (FF0000) | |
| Engrave color | Black (000000) | |

### Manual Focusing Procedure

The automatic ZOffset cannot safely raise the table enough to focus at the material midplane (~3mm into 5.75mm HDF) because the working distance is too close to the lens assembly. Instead:

1. **Calibrate focus** using the physical gap tool (sets focal plane to material surface)
2. **Manually raise the table** ~3mm using the GUI Z-axis controls to place the focal plane at the material midplane
3. **Do NOT use ZOffset** for cuts — leave at 0, since the table is already positioned
4. **For engraving**: if engraving is needed on the same job, set the Engrave effect ZOffset to +3mm (table down) to compensate and focus back on the surface

## Grid Sweep Results

Three parameter sweeps were run (test SVGs in `test-patterns/`):

### Grid 1: Speed × Passes (1kHz)

| | 1 pass | 2 pass | 3 pass | 4 pass |
|---|---|---|---|---|
| **3%** | no | no | no | no |
| **2%** | no | no | no | no |
| **1%** | no | no | no | no |
| **0.5%** | no | **yes** | yes | yes |
| **0.25%** | yes | yes | yes | yes |

### Grid 2: Speed × Frequency (2 passes)

| | 1kHz | 5kHz | 10kHz | 20kHz |
|---|---|---|---|---|
| **0.25%** | yes | yes | **best** | yes |
| **0.5%** | no | no | no | no |
| **0.75%** | no | no | no | no |
| **1.0%** | no | no | no | no |

10kHz / 0.25% had the cleanest cut-through.

### Grid 3: Passes × Speed (10kHz)

| | S 0.25% | S 0.5% | S 1% | S 2% |
|---|---|---|---|---|
| **2 pass** | yes | borderline | no | no |
| **3 pass** | yes | **selected** | no | no |
| **4 pass** | yes | yes | borderline | no |
| **5 pass** | yes | yes | yes | no |
| **6 pass** | yes | yes | yes | borderline |
| **8 pass** | yes | yes | yes | yes |

**Previously selected**: 0.5% / 3 passes as best balance of speed and cut quality.

### Focal Sweep Test (2026-04-29): Passes × Frequency

| | 1kHz | 3kHz | 5kHz |
|---|---|---|---|
| **3 pass** | no | no | no |
| **4 pass** | not tested (stopped) | not tested | not tested |
| **5 pass** | not tested (stopped) | not tested | **yes — clean cut** |

Job was stopped early (flame-up). Bottom-right cell (5kHz / 5 pass) had a clean cut-through.

**Updated selection**: 0.5% / 5 passes / 5kHz / ZOffset 0.

## Measured Kerf

### With midplane focus (current best settings)

From 4.3mm alignment pins (kerf +0.15mm, S0.3% / 1 pass / 1kHz, manual midplane focus):

| Measurement | Value |
|-------------|-------|
| Top width | 4.08 mm |
| Bottom width | 4.05 mm |
| Top kerf (per side) | ~0.11 mm |
| Bottom kerf (per side) | ~0.125 mm |
| Taper | ~0.3° (essentially parallel) |
| Material thickness | 5.75 mm (nominal 6mm) |

Midplane focus virtually eliminates taper.

### Without midplane focus (surface focus, old data)

From an 8mm circle cut (0.25% / 2 pass / 1kHz, focus on surface):

| Measurement | Value |
|-------------|-------|
| Top diameter | 7.95 mm |
| Bottom diameter | 7.05 mm |
| Top kerf (per side) | ~0.025 mm |
| Bottom kerf (per side) | ~0.475 mm |
| Taper | ~7° |

The taper with surface focus is significant — nearly 1mm difference between top and bottom.

## Known Issues

- **Heavy charring** at the slow speeds required. Surface char and dark kerf walls.
- **~7° taper** — cut walls are not perpendicular. Top is tight, bottom is wide.
- **60W RF tube is marginal** for 6mm cuts. A 100W DC tube would allow faster single-pass cuts with less charring.

## Z-Axis / ZOffset Convention (Confirmed 2026-04-29)

**Positive ZOffset = table moves DOWN = focus moves ABOVE material surface.**
**Negative ZOffset = table moves UP = focus moves INTO material.**

This is the opposite of what the Ruby docs imply. Confirmed by physical observation: with ZOffset +5.75, the table visibly moved away from the lens assembly.

### Implications for Focal Sweep

A focal sweep through 5.75mm material would require negative ZOffset values (table up, focus deeper). However:
- The machine rejects Z positions below `StartingZPosition` (set when job begins)
- Only ~4mm physical clearance between material surface and lens assembly
- **Max safe table-up movement: ~3.5mm** — not enough to reach bottom of 5.75mm material

**Conclusion**: focal plane sweep is not practical with this setup. Multi-pass at surface focus (ZOffset 0) is the working approach. The 5kHz / 5-pass result confirms this works well.

### Focal Sweep Test Results (2026-04-29)

Ran `cut-focal-sweep.svg` — 9 cells (1/3/5 kHz × 3/4/5 passes) with ZOffset walking through material depth per pass. ZOffset was positive so focus actually moved ABOVE material (wrong direction). Despite this, the **5kHz / 5-pass cell cut cleanly** — confirming that extra passes and moderate frequency are what matter, not focal position.

## Troubleshooting & Future Optimization

### Beam Alignment Check
The taper may indicate the beam is not centered in the lens. **Test**: pulse at two different Z heights (10mm apart); burn marks should overlap perfectly. If offset, the beam enters the lens off-center, causing angled refraction.

### Frequency
Trotec recommends **low frequency (1000 Hz)** for MDF to produce bright cutting edges. Our 10kHz improves cut-through but may increase charring. Worth re-testing 1kHz with 3+ passes.

### Lens Focal Length
- **1.5" FL**: Tighter beam, less kerf, less depth of focus — better for thin material
- **2.0" FL**: Standard, good for up to ~6mm
- **2.5" FL**: More depth of focus (less taper) but wider kerf — may help with thick material

Check what lens is currently installed. A 2.5" lens could reduce the taper at the cost of a wider kerf.

### Air Assist
Aquarium pump pressure is sufficient. Excessive air pressure can blow flames into the kerf. Nozzle should be close to the material surface.

### Smoke Extraction
Good extraction from the cut zone reduces redeposit charring on the surface. Visible smoke being pulled away from the workpiece indicates adequate airflow.

### Surface Protection
Apply masking tape to the material surface before cutting to reduce char marks on the face.

### Confirmed: This is HDF, Not MDF
Weighed a 1000×600×6mm sheet at **3100g** → density **~861 kg/m³**.
- MDF (700-750 kg/m³): would weigh ~2.5-2.7 kg
- **HDF (850-1000 kg/m³): 3.1 kg ✓**

This explains the difficulty cutting through with 60W. HDF has ~20% resin content (vs 10-15% for MDF) and is pressed at higher pressure, making it significantly harder to cut. It does produce cleaner edges once you get through, but demands more power.

### Single Pass at Higher Power
Multiple passes compound the heat-affected zone. If a 100W DC tube were installed, single-pass cutting at faster speeds would be possible, dramatically reducing charring.

## Ruby API Material Configuration

The MDF material profile is stored in Ruby's material database and can be updated via the API:

```python
from ruby_client import RubyClient
client = RubyClient()
client.sign_in()

# Read current settings
resp = client.session.get('https://localhost:5001/api/Material/GetMaterials')
mdf = resp.json()['materials'][0]

# Update a parameter
for el in mdf['effects'][1]['elements']:  # effects[1] = Cut
    if el['key'] == 'Speed': el['value'] = 0.5
    if el['key'] == 'Passes': el['value'] = 3

# Save
client.session.put('https://localhost:5001/api/Material/SaveMaterial',
    json=mdf, headers={'Content-Type': 'application/json'})
```

### Parameter Ranges (from API metadata)

| Parameter | Min | Max | Type |
|-----------|-----|-----|------|
| Power | 0 | 100 | % |
| Speed | 0.01 | 100 | % |
| Frequency | 1,000 | 60,000 | Hz |
| Passes | 1 | 100 | integer |
| ZOffset | -5 | 20 | mm |

## Production Cut Times

| Sheet | Panels | Utilization | Cut Time | Notes |
|-------|--------|-------------|----------|-------|
| sheet1_v2 | 16 | 83% | 39:43 | 950×550mm, 1kHz, S0.3%, 1 pass |
| sheet2_v2 | 18 | 74% | — | |
| sheet3_v2 | 26 | 72% | — | |

## Test Pattern SVGs

Parameter sweep test patterns are in `test-patterns/`:
- `cut-param-sweep.svg` — initial 7-line speed/pass sweep
- `cut-grid-test.svg` — Grid 1: speed × passes at 1kHz
- `cut-grid-test2.svg` — Grid 2: speed × frequency at 2 passes
- `cut-grid-test3.svg` — Grid 3: passes × speed at 10kHz
- `cut-focal-sweep.svg` — Focal sweep: 3 freq × 3 pass counts, Z walked per pass (confirmed ZOffset direction is opposite to expected)
- `generate_focal_sweep.py` — Generator script for focal sweep SVG + effect JSON

Each SVG uses unique stroke colors per test cell. The MDF material database in Ruby is configured with matching color→effect mappings during testing (then reset to standard red=cut after).
