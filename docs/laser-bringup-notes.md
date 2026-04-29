# Bringing a Trotec Q400 Laser Online with Claude Code

## Overview

This document describes the full process of bringing a Trotec Q400 RF CO2 laser cutter online, remotely controlled by an AI agent (Claude Code), from zero to cutting parts. The laser is physically connected to a Windows PC via USB. The AI agent runs on a Mac and communicates with the laser through SSH tunnels and the Trotec Ruby REST API.

The goal: let Claude Code upload SVG cut files, configure material settings, manage the job queue, and monitor the laser — all programmatically, without touching the Ruby GUI.

## Hardware Setup

- **Laser**: Trotec Q400_RF — a mid-range flatbed CO2 laser with a 60W CeramiCore RF-excited tube
- **Work area**: 1034 × 631 mm
- **Z travel**: 200mm (coordinates -0.1 to -199.9mm, all negative — less negative = table higher)
- **Serial**: Q42-3066
- **Controller PC**: Windows MiniPC (MiniPC_103) at 10.160.26.28, connected to laser via USB
- **Trotec Ruby**: v2.11.1 — Trotec's web-based laser management software, runs on the Windows PC
- **Client**: MacBook running Claude Code (the AI agent)
- **Material**: 6mm MDF (Italian-sourced, 1000×600mm sheets)

## Phase 1: SSH Connectivity

The first challenge was establishing a reliable connection from the Mac to the Windows PC on the local network.

### Installing OpenSSH on Windows

The Windows PC didn't have SSH enabled. We installed OpenSSH Server via PowerShell:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

A firewall rule was needed to allow inbound SSH:

```powershell
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### SSH Key Authentication

Standard `~/.ssh/authorized_keys` didn't work because the Windows user was an administrator. Windows OpenSSH requires admin keys in a different location:

```
C:\ProgramData\ssh\administrators_authorized_keys
```

We generated a dedicated key pair (`~/.ssh/trotec-tunnel`) and configured an SSH alias:

```
# ~/.ssh/config
Host trotec
  HostName 10.160.26.28
  User Shamrock
  IdentityFile ~/.ssh/trotec-tunnel
```

### Rate Limiting Gotcha

During initial troubleshooting, too many failed auth attempts triggered SSH rate limiting ("Connection timed out during banner exchange"). The fix was simply waiting 10+ seconds for the lockout to expire.

## Phase 2: SSH Tunnels

Trotec Ruby runs multiple HTTPS services on localhost. We needed to forward these ports through the SSH tunnel to the Mac.

### Discovering the Ports

We scraped the Ruby web UI's JavaScript bundles to find all service endpoints:

| Port  | Protocol | Service |
|-------|----------|---------|
| 2402  | HTTPS | Ruby Web UI (Angular SPA) |
| 5001  | HTTPS | Ruby WebAPI (REST + Swagger) |
| 5016  | HTTPS | Ruby Manager / TrayApp |
| 5043  | HTTPS | Hot Status |
| 27200 | HTTP | JobManager |

**Critical discovery**: all services use HTTPS with self-signed certificates, not HTTP. Early attempts with HTTP returned empty responses, which was confusing until we realized the protocol mismatch.

### Tunnel Manager

We built `tunnel.sh`, a config-driven tunnel manager. Configuration lives in `tunnel.config.json`:

```json
{
  "host": "trotec",
  "tunnels": {
    "ruby-api": {
      "description": "Trotec Ruby OpenAPI / Swagger (HTTPS)",
      "localPort": 5001,
      "remotePort": 5001
    },
    "ruby-laser": {
      "description": "Trotec Ruby laser web UI (HTTPS)",
      "localPort": 2402,
      "remotePort": 2402
    }
  }
}
```

Commands: `./tunnel.sh up`, `./tunnel.sh down`, `./tunnel.sh status`, `./tunnel.sh test`

Each tunnel runs as a background SSH process with PID tracking in `.pids/`. The `test` command verifies HTTPS connectivity through each tunnel.

### WiFi Instability

The Windows PC connects via WiFi with ~1400ms ping times. Tunnel connections drop frequently. We bounce tunnels (`down` then `up`) as needed. A future improvement would be automatic reconnection or switching to a wired connection.

## Phase 3: Ruby API Authentication

### Finding the Auth Endpoint

The Swagger docs at `https://localhost:5001/swagger/index.html` document the "OpenAPI" endpoints but not the internal ones. We found the auth endpoint by reading the Ruby SPA's JavaScript bundle:

```
POST /api/User/SignIn
Body: {"email": "...", "password": "..."}
Response: {"token": "...", "name": "...", "email": "...", "roles": [...]}
```

The token is a JWT used as a Bearer token for subsequent requests.

### Session Conflicts

A major pain point: Ruby apparently supports only one active session per user. When the human operator was logged into the Ruby GUI and the API client was also making authenticated requests with the same account, they would kick each other out — causing intermittent 401 errors and confusing failures.

### Claude Service Account

The solution was creating a dedicated service account for the AI agent:

```python
# Created via the API with the human's Superadmin account
POST /api/User/Register
{
  "email": "claude@trotec.local",
  "password": "TrotecAgent2026!",
  "name": "Claude (API Agent)",
  "roles": ["Admin", "MdbAdmin", "User"]
}
```

This eliminated session conflicts — the human uses the GUI with their personal account, and Claude uses the API with its own account. Credentials are stored in `.env` (gitignored).

### PersonalAccessToken (PAT)

Some OpenAPI endpoints require a PAT instead of a JWT:

```
POST /api/User/GeneratePersonalAccessToken
Authorization: Bearer <JWT>
Response: "<PAT string>"

# Then use as:
Authorization: PersonalAccessToken <PAT>
```

## Phase 4: Device Registration

### The "No Laser Connected" Problem

After establishing API access, all device control endpoints returned errors. The Ruby process list showed `PlotterProcess` was down with `NoDeviceSelectedInConfig`. The laser was physically connected via USB but not registered in Ruby's configuration.

### Finding the Serial Number

We read the serial number (Q42-3066) from the physical nameplate on the back of the laser. This was confirmed by probing the USB bus on the Windows machine.

### Cloud Calibration

Trotec devices require cloud-based calibration data. The registration process was:

1. **Verify with Trotec cloud**:
   ```
   POST /api/Proxy/VerifyCloudDeviceConfig?serialNo=Q42-3066
   ```
   This returned the correct model identifier (`Q400_RF`) — important because "RF" means RF-excited CO2, not a different laser type.

2. **Add the device**:
   ```
   POST /api/Proxy/AddDevice?serialNo=Q42-3066&modelId=Q400_RF&deviceConfigSource=TrotecSettings&machineLayer=Plotter
   ```
   This downloads calibration data from Trotec's cloud servers. Over the slow WiFi connection, this took several minutes and required increasing the HTTP timeout to 300 seconds.

3. **MachineLayer config**: The registration writes to `C:\ProgramData\Trotec\JobDispatcher.ConsoleServer\Config.xml`, setting `MachineModelNumber` from `None` to `Q400_RF`.

After registration, `PlotterProcess` came up as `Running` and the device reported `status: Idle`.

### The x-target-device Header

Device control endpoints require an `x-target-device: Q42-3066` header. Without it, you get `ERR_QUEUE_000` ("No device connected/selected"). This wasn't obvious from the Swagger docs.

## Phase 5: Python Client Library

We built `ruby_client.py` — a clean Python wrapper around the Ruby REST API using `requests`. Key design decisions:

- **`requests.Session`** with `verify=False` for self-signed certs
- **`python-dotenv`** for credential management from `.env`
- **Empty response handling**: many Ruby endpoints return empty bodies in certain states, which causes `resp.json()` to throw. Every method checks `if not resp.content` before parsing.
- **CLI interface**: `uv run python ruby_client.py status|upload|designs|queue|logs|...`

The `logs` command reads Ruby service logs from the Windows machine via SSH, which proved invaluable for debugging Z-axis movements and job execution:

```bash
uv run python ruby_client.py logs ml 50    # MachineLayer log
uv run python ruby_client.py logs nc 50    # Numerical control commands
uv run python ruby_client.py logs issues   # Issue history
```

## Phase 6: File Upload

### The Upload Endpoint

SVG files are uploaded via multipart form POST:

```
POST /api/FileUpload/Upload
Content-Type: multipart/form-data
Field name: "uploadedFile"  ← this exact field name is required
```

Early attempts used the field name `file`, which returned `ERR_FILEUPLOAD_002`. The correct field name was found by inspecting the Ruby SPA's upload form.

### Design vs Workbench

An important workflow concept in Ruby:

1. **Upload** creates a **Design** — the raw file in Ruby's library
2. A **Workbench** is created by placing a design onto the virtual work area (done in the GUI)
3. The workbench is **enqueued** and **run** to execute the cut

We could not find an API endpoint to programmatically create a workbench from a design. This step currently requires the Ruby GUI — drag the design onto the work area and assign a material profile.

### Per-User Design Scope

Designs are scoped to the user who uploaded them. When Claude uploaded files with its service account, the human couldn't see them in the GUI (logged in with a different account). Solution: upload under the human's account for GUI-based workflows.

## Phase 7: Z-Axis Focus Control

### The Coordinate System

The Q400's Z-axis uses all-negative coordinates:
- **Z = -0.1**: table at highest position (closest to laser head)
- **Z = -199.9**: table at lowest position (furthest from laser head)
- **Less negative = higher = closer to head**

### Focus Calibration

The laser was calibrated using the physical gap tool, which sets the focal distance to the material surface. With the gap tool, the table was positioned at Z ≈ -188.19mm.

For 6mm MDF, the focal point should be at the midplane (3mm into the material), requiring the table to move UP 3mm.

### ZOffset in Material Settings

Ruby's material database has a `ZOffset` parameter per effect (Cut, Engrave):
- **ZOffset = 0**: focus on material surface
- **ZOffset = +3**: table moves UP 3mm → focus 3mm into material
- **ZOffset = -3**: table moves DOWN 3mm → focus 3mm above material

We initially got the sign wrong, setting ZOffset to -3 (table down). This triggered `ZMoveNotAllowed` errors because the system refused to move below the starting position. Reading the MachineLayer logs (`log_ML.log`) revealed the exact calculation:

```
ZMoveHandler.MoveFocusAxisAsync: failed.
_movingUnit.CanMoveToZPosition(-191.190246,
  _allowNegativeZPositionAbsolute(False) ||
  zPosition(-191.190246) >= StartingZPosition(-188.190246)) = False
```

The logs also confirmed that ZOffset = +3 **does work correctly**:

```
ZMoveHandler.MoveFocusAxisAsync: move to new Z-Position (-188.190246 -> -185.190246)
```

And at job completion, it moves back:

```
ZMoveHandler.ResetHeadAxisAsync: try move back to StartingZPosition (-185.190327 -> -188.190246)
```

### Workbench Caching

A critical gotcha: **workbenches cache the material settings from when they were created**. Updating the material database via the API does NOT retroactively update existing workbenches. You must delete the workbench and create a new one for updated settings to take effect. This caused several confusing test cycles where we changed ZOffset but the job ran with old values.

## Phase 8: Material Parameter Optimization

### The Problem

Initial cuts on 6mm MDF with default settings (Power 100%, Speed 3%, 1 pass, 1kHz) didn't cut through. We needed to find optimal parameters empirically.

### The Multi-Color Grid Sweep Method

Ruby maps SVG stroke colors to material effects. We exploited this to run parameter sweeps in a single job:

1. **Create an SVG** with a grid of circles, each a different color
2. **Add a Cut effect** for each color in the material database, each with different speed/passes/frequency
3. **Upload and run** — one job tests 20+ parameter combinations simultaneously
4. **Inspect results** — push out the circles. The ones that fall out cleanly are the winning parameters.

For example, `cut-grid-test.svg` has 20 circles in a 5×4 grid (5 speeds × 4 pass counts), each with a unique hex color:

```
              1 pass    2 pass    3 pass    4 pass
Spd 3%      #FF0000   #FF3300   #FF6600   #FF9900
Spd 2%      #CC0000   #CC3300   #CC6600   #CC9900
Spd 1%      #990000   #993300   #996600   #999900
Spd 0.5%    #660000   #663300   #666600   #669900
Spd 0.25%   #330000   #333300   #336600   #339900
```

The material database is updated via the API to create 20 Cut effects, one per color:

```python
def make_cut(eid, color, speed, passes, freq):
    e = copy.deepcopy(cut_template)
    e['id'] = eid
    e['layers'] = [color]
    for el in e['elements']:
        if el['key'] == 'Speed': el['value'] = speed
        if el['key'] == 'Passes': el['value'] = passes
        # ...
    return e

mdf['effects'] = [engrave_effect,
    make_cut(2, 'FF0000', 3, 1, 1000),
    make_cut(3, 'FF3300', 3, 2, 1000),
    # ... 18 more
]
client.session.put('.../api/Material/SaveMaterial', json=mdf)
```

### Three Grid Sweeps

**Grid 1: Speed × Passes (1kHz)**
- Only 0.25% and 0.5% speeds cut through
- Minimum viable: 0.5% speed, 2 passes

**Grid 2: Speed × Frequency (2 passes)**
- Higher frequency (10kHz) improved cut-through at same speed
- 0.25% / 10kHz was the cleanest

**Grid 3: Passes × Speed (10kHz)**
- More passes at faster speed = less charring than fewer passes at slower speed
- Selected: 0.5% / 3 passes as best balance

### Optimal Settings

| Parameter | Value |
|-----------|-------|
| Power | 100% |
| Speed | 0.5% |
| Passes | 3 |
| Frequency | 10,000 Hz |
| ZOffset | +3 mm |
| AirAssist | On |

### Kerf Measurements

From an 8mm test circle:
- Top diameter: 7.95mm → kerf 0.025mm/side (very tight)
- Bottom diameter: 7.05mm → kerf 0.475mm/side (beam diverged)
- Taper angle: ~7°
- The taper is inherent to CO2 laser physics on thick material

### Remaining Issues

- **Heavy charring** at the slow speeds required — the 60W RF tube is at its limit for 6mm
- **~7° taper** — cut walls are not perpendicular
- Possible **beam misalignment** contributing to taper (needs pulse test at two Z heights)
- The Italian-sourced material may be **HDF** (denser than standard MDF), requiring more power

## Phase 9: Cutting the Actual Parts

### Cube-Resonator Design

The target project is a laminated loudspeaker cabinet (cube-resonator) made from stacked laser-cut MDF layers. The design tool (`../cube-resonator/cabinet-design/`) generates:
- Individual part SVGs for each layer (front, side, back wall variants)
- Nested sheet SVGs that pack all parts onto stock sheets

### Sheet Nesting

The nesting tool (`nesting.py`) uses shelf-based bin packing with configurable parameters:

```bash
python3 nesting.py --all --sheet 1000x600 --gap 2.0
```

Initial sheets were generated at 1010×610mm (matching the Q400 bed size), but our MDF stock is 1000×600mm. We regenerated at the correct size.

### Disabling Engrave

The design SVGs include blue text labels for human reference (layer names, dimensions). These were being engraved onto the material, wasting time and marking the surface. We disabled the Engrave effect in the material database:

```python
for effect in mdf['effects']:
    if effect['process'] == 'Engrave':
        effect['enabled'] = 0
```

### Stock Alignment

The Q400's coordinate origin is top-left (where the laser head homes). MDF stock should be placed flush against the top-left corner of the bed.

## Tools Built

| Tool | Purpose |
|------|---------|
| `tunnel.sh` | SSH tunnel lifecycle manager |
| `tunnel.config.json` | Tunnel port configuration |
| `ruby_client.py` | Python client library + CLI for Ruby API |
| `laser.sh` | Bash CLI for quick laser operations |
| `test-patterns/*.svg` | Parameter sweep test patterns |
| `materials/MDF-6mm.md` | Empirical material profile |

## Key Lessons

1. **Ruby's API is powerful but underdocumented.** The Swagger docs cover OpenAPI endpoints but miss internal ones (auth, device control, material database). Reverse-engineering the SPA's JavaScript was essential.

2. **Workbenches cache material settings.** Always delete and recreate workbenches after changing material parameters. This caused the most confusing debugging sessions.

3. **Session conflicts are real.** Dedicated service accounts for API agents are essential when humans are also using the GUI.

4. **The machine logs are invaluable.** `log_ML.log` on the Windows host shows exact Z positions, job execution steps, and error details that the API doesn't expose.

5. **Parameter sweeps via color mapping is extremely efficient.** Testing 20+ combinations in a single job (rather than 20 separate jobs) saved hours of iteration time.

6. **60W RF tubes are marginal for 6mm MDF cutting.** The CeramiCore RF tube in the Q400 is optimized for engraving quality, not cutting power. A DC tube upgrade would dramatically improve thick-material cutting.

7. **WiFi is a bottleneck.** The SSH tunnels drop frequently over WiFi. A wired Ethernet connection to the Windows PC would improve reliability significantly.

8. **ZOffset sign convention matters.** Positive ZOffset = table UP = focus deeper into material. We got this wrong initially and wasted several test cycles before the machine logs revealed the actual behavior.
