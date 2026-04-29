# MDF 6mm — Cut Profile for Trotec Q400_RF

**Machine**: Trotec Q400_RF (serial Q42-3066, 60W CeramiCore RF CO2)
**Date tested**: 2026-04-28
**Stock**: 6mm HDF (Italian-sourced, confirmed ~861 kg/m³ — see density measurement below)

## Current Best Settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| Power | 100% | Maximum required for 6mm |
| Speed | 0.5% | Slowest reliable cut-through |
| Passes | 3 | Multi-pass required at 60W |
| Frequency | 10,000 Hz | Higher freq improved cut-through |
| ZOffset | +3 mm | Table up — focal point at midplane |
| AirAssist | On | Standard |
| PowerCorrection | 7% | Default |

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

**Selected**: 0.5% / 3 passes as best balance of speed and cut quality.

## Measured Kerf

From an 8mm circle cut (0.25% / 2 pass / 1kHz):

| Measurement | Value |
|-------------|-------|
| Top diameter | 7.95 mm |
| Bottom diameter | 7.05 mm |
| Top kerf (per side) | ~0.025 mm |
| Bottom kerf (per side) | ~0.475 mm |
| Taper | ~7° |
| Material thickness | 5.75 mm (nominal 6mm) |

The taper is significant — nearly 1mm difference between top and bottom of the cut.

## Known Issues

- **Heavy charring** at the slow speeds required. Surface char and dark kerf walls.
- **~7° taper** — cut walls are not perpendicular. Top is tight, bottom is wide.
- **60W RF tube is marginal** for 6mm cuts. A 100W DC tube would allow faster single-pass cuts with less charring.

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

## Test Pattern SVGs

Parameter sweep test patterns are in `test-patterns/`:
- `cut-param-sweep.svg` — initial 7-line speed/pass sweep
- `cut-grid-test.svg` — Grid 1: speed × passes at 1kHz
- `cut-grid-test2.svg` — Grid 2: speed × frequency at 2 passes
- `cut-grid-test3.svg` — Grid 3: passes × speed at 10kHz

Each SVG uses unique stroke colors per test cell. The MDF material database in Ruby is configured with matching color→effect mappings during testing (then reset to standard red=cut after).
