# trotec-tools

Tools for controlling a Trotec laser cutter via the Ruby API, designed to be driven by AI agents (Claude Code) over SSH tunnels.

## What is this?

Trotec's **Ruby** software runs on a Windows PC connected to the laser via USB. It exposes a rich REST API on localhost. This project provides:

1. **SSH tunnel manager** — securely forward the Ruby API ports to your local machine
2. **Python client library** — clean interface to the Ruby API for uploading designs, controlling the laser, and monitoring status
3. **CLI tools** — bash and Python scripts for quick laser operations

The goal is to let **Claude Code** (or any AI agent) pilot a Trotec laser: upload SVG cut files, manage the job queue, monitor device status, and control the machine — all through the API.

## Supported Hardware

Currently tested with:
- **Trotec Q400** (RF-excited CO2 laser)
- **Trotec Ruby** v2.11.1

The Ruby API is common across Trotec's product line, so this should work with other models (Speedy, R-series, etc.) with minimal changes.

## Quick Start

### 1. Prerequisites

- A Trotec laser with Ruby software running on a Windows PC
- SSH access to the Windows PC ([OpenSSH for Windows](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse))
- [uv](https://docs.astral.sh/uv/) for Python environment management

### 2. Setup

```bash
git clone https://github.com/project-shamrock/trotec-tools.git
cd trotec-tools

# Configure credentials
cp .env.example .env
# Edit .env with your Ruby login and device info

# Configure SSH (add to ~/.ssh/config)
# Host trotec
#   HostName <windows-ip>
#   User <windows-user>
#   IdentityFile ~/.ssh/trotec-tunnel

# Install Python dependencies
uv sync
```

### 3. Open Tunnels

```bash
./tunnel.sh up        # open all tunnels
./tunnel.sh status    # verify they're running
./tunnel.sh test      # test HTTPS connectivity
```

### 4. Use the Python Client

```bash
# Full status report
uv run python ruby_client.py status

# Upload a design
uv run python ruby_client.py upload my-design.svg

# Check designs and queue
uv run python ruby_client.py designs
uv run python ruby_client.py queue
```

### 5. Use as a Library

```python
from ruby_client import RubyClient

client = RubyClient()
client.sign_in()

# Check laser status
status = client.get_device_status()
print(f"Laser is {status['status']}")

# Upload and queue a job
client.upload_file("cut-pattern.svg")
designs = client.get_designs()
# ... enqueue, run, monitor
```

## Architecture

```
┌─────────────┐     SSH Tunnel      ┌──────────────────┐     USB      ┌─────────────┐
│  Your Mac   │ ──────────────────> │  Windows PC      │ ──────────> │  Trotec     │
│  Claude Code│    ports 2402,5001  │  Ruby v2.11.1    │    COM port  │  Laser      │
│  Python     │                     │  (Kestrel/HTTPS) │              │             │
└─────────────┘                     └──────────────────┘              └─────────────┘
```

## Ruby API Services

| Port  | Protocol | Service                         |
|-------|----------|---------------------------------|
| 2402  | HTTPS    | Ruby Web UI (Angular SPA)       |
| 5001  | HTTPS    | Ruby WebAPI (REST + Swagger)    |
| 5016  | HTTPS    | Ruby Manager / TrayApp          |
| 5043  | HTTPS    | Hot Status                      |
| 27200 | HTTP     | JobManager                      |

## API Endpoints

### OpenAPI (documented)

Swagger UI: `https://localhost:5001/swagger/index.html`

| Method | Endpoint                | Description                    |
|--------|-------------------------|--------------------------------|
| POST   | /api/OpenApi/Upload     | Upload a design file           |
| GET    | /api/OpenApi/GetDesigns | List designs                   |
| GET    | /api/OpenApi/GetWorkbenches | List workbenches           |
| POST   | /api/OpenApi/EnqueueWorkbench | Send to queue            |
| GET    | /api/OpenApi/GetDeviceStatus | Laser status              |
| GET    | /api/OpenApi/GetJobsStatus | Job progress                |
| GET    | /api/OpenApi/GetQueueElements | Queue contents          |
| GET    | /api/OpenApi/GetTableCameraStream | Live camera         |

### Internal API (undocumented, reverse-engineered)

| Method | Endpoint                           | Description              |
|--------|------------------------------------|--------------------------|
| POST   | /api/User/SignIn                   | Authenticate, get JWT    |
| GET    | /api/Diagnostics/GetProcessesState | Service health           |
| GET    | /api/Proxy/ListDevices             | Connected lasers         |
| POST   | /api/Proxy/AddDevice               | Register a laser         |
| PUT    | /api/Device/MoveZ                  | Move Z stage             |
| POST   | /api/Queue/RunQueue                | Start cutting            |
| POST   | /api/Queue/Stop                    | Emergency stop           |
| GET    | /api/Camera/Frame                  | Camera snapshot          |

See `docs/swagger.json` for the full OpenAPI spec.

## Tunnel Management

```bash
./tunnel.sh up [name]      # Open tunnel(s)
./tunnel.sh down [name]    # Close tunnel(s)
./tunnel.sh status         # Show tunnel status
./tunnel.sh list           # List configured tunnels
./tunnel.sh test           # Test HTTPS connectivity
./tunnel.sh ssh            # Interactive SSH session
./tunnel.sh exec <cmd>     # Run remote command
```

## Troubleshooting

### Common Error Codes

| Code | Meaning |
|------|---------|
| ERR_QUEUE_000 | No device connected/selected |
| ERR_QUEUE_007 | Device not ready (needs homing/init) |
| ERR_DEVCOM_006 | Table move rejected (close lid, turn key) |
| ERR_GENERAL_100 | Missing or invalid parameter |
| ERR_TRB_005 | Cloud calibration download failed |

### First-Time Device Setup

If the laser has never been configured with Ruby:

```bash
# 1. Verify laser serial with Trotec cloud
curl -sk "https://localhost:5001/api/Proxy/VerifyCloudDeviceConfig?serialNo=YOUR-SERIAL" \
  -X POST -H "Authorization: Bearer $TOKEN"

# 2. Add the device (uses cloud calibration — can take minutes)
curl -sk "https://localhost:5001/api/Proxy/AddDevice?serialNo=YOUR-SERIAL&modelId=MODEL&deviceConfigSource=TrotecSettings&machineLayer=Plotter" \
  -X POST -H "Authorization: Bearer $TOKEN"
```

## License

MIT

## Acknowledgments

Built with [Claude Code](https://claude.ai/code) by [project-shamrock](https://github.com/project-shamrock).
