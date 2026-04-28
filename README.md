# trotec-tunnel

A tunneling service that exposes a Trotec Q400 RF laser (serial `Q42-3066`) connected to a remote Windows host over the network via SSH tunnels and the Trotec Ruby API.

## Architecture

```
[ Client (Mac) ] --SSH Tunnel--> [ Windows Host (MiniPC_103) ] --USB/COM3--> [ Trotec Q400 Laser ]
                                  10.160.26.28
                                  Ruby v2.11.1
```

The Windows machine runs **Trotec Ruby** software (v2.11.1) which exposes several local services. We tunnel into them over SSH to control the laser remotely.

## Services on the Windows Host

| Port  | Protocol | Service                         |
|-------|----------|---------------------------------|
| 2402  | HTTPS    | Ruby Web UI (Angular SPA)       |
| 5001  | HTTPS    | Ruby WebAPI (REST + Swagger)    |
| 5016  | HTTPS    | Ruby Manager / TrayApp          |
| 5043  | HTTPS    | Hot Status                      |
| 27200 | HTTP     | JobManager                      |
| 5000  | HTTP     | Certificate service             |
| 46146 | HTTPS    | Auto-updater                    |

## Quick Start

### 1. Open Tunnels

```bash
./tunnel.sh up        # opens all configured tunnels
./tunnel.sh status    # verify tunnels are running
./tunnel.sh test      # test HTTPS connectivity
```

### 2. Access the Laser

- **Ruby Web UI**: https://localhost:2402
- **Swagger Docs**: https://localhost:5001/swagger/index.html
- **API Base**: https://localhost:5001/api/OpenApi/

### 3. Authenticate

```bash
# Sign in to get a JWT token
curl -sk https://localhost:5001/api/User/SignIn \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"r.j.walters@gmail.com","password":"Shamrock1"}'
```

Use the returned `token` field as a Bearer token:

```bash
curl -sk https://localhost:5001/api/OpenApi/GetDeviceStatus \
  -H "Authorization: Bearer <token>" \
  -H "x-api-version: 1.0-OpenApi"
```

## Tunnel Management

```bash
./tunnel.sh up [name]      # Open tunnel(s)
./tunnel.sh down [name]    # Close tunnel(s)
./tunnel.sh status         # Show tunnel status
./tunnel.sh list           # List available tunnels
./tunnel.sh test           # Test HTTPS connectivity
./tunnel.sh ssh            # Interactive SSH to Windows host
./tunnel.sh exec <cmd>     # Run command on Windows host
```

Tunnels are defined in `tunnel.config.json`.

## SSH Setup

- SSH host alias: `trotec` (configured in `~/.ssh/config`)
- Key: `~/.ssh/trotec-tunnel` (ed25519)
- Windows user: `Shamrock@10.160.26.28`
- OpenSSH for Windows on the host, key in `C:\ProgramData\ssh\administrators_authorized_keys`

## API Endpoints (OpenAPI)

Available at `https://localhost:5001/api/OpenApi/`:

| Method | Endpoint                | Description                    |
|--------|-------------------------|--------------------------------|
| POST   | Upload                  | Upload a design file           |
| POST   | UploadFromMany          | Upload multiple files          |
| POST   | UploadFromDesign        | Upload from existing design    |
| POST   | UploadFromManyDesigns   | Upload from multiple designs   |
| POST   | EnqueueWorkbench        | Send workbench to queue        |
| GET    | GetDesigns              | List designs                   |
| GET    | GetWorkbenches          | List workbenches               |
| GET    | GetQueueElements        | List queue entries             |
| DELETE | DeleteAllItems          | Clear all items                |
| DELETE | DeleteDesign            | Delete a design                |
| DELETE | DeleteWorkbench         | Delete a workbench             |
| DELETE | DeleteQueueElement      | Remove queue entry             |
| GET    | GetDeviceStatus         | Laser hardware status          |
| GET    | GetJobsStatus           | Running job status             |
| GET    | GetImportProfiles       | Available import profiles      |
| GET    | GetTableCameraStream    | Live table camera feed         |

Full internal API (non-OpenAPI) is also available with many more endpoints — see `docs/swagger.json` and the internal API docs below.

## Internal API Endpoints (Selected)

These are not in the OpenAPI spec but are available on port 5001:

| Method | Endpoint                          | Description                    |
|--------|-----------------------------------|--------------------------------|
| POST   | /api/User/SignIn                  | Authenticate, get JWT          |
| POST   | /api/User/SignOut                 | Sign out                       |
| GET    | /api/Diagnostics/GetProcessesState| Ruby service health            |
| GET    | /api/Proxy/ListDevices            | List connected lasers          |
| POST   | /api/Proxy/AddDevice              | Register a laser               |
| GET    | /api/Info/GetVersionInfo          | Ruby version info              |
| GET    | /api/Queue/GetQueue               | Full queue state               |
| POST   | /api/Queue/RunQueue               | Start processing queue         |
| POST   | /api/Queue/Stop                   | Stop queue                     |
| GET    | /api/Device/SetKeyStatus          | Key switch status              |
| GET    | /api/Camera/Devices               | Camera devices                 |
| GET    | /api/Camera/Frame                 | Camera frame capture           |
| GET    | /api/Settings/GetDeviceSettings   | Device configuration           |

## Device Info

- **Model**: Trotec Q400 RF (CO2 laser, RF-excited)
- **Serial**: Q42-3066
- **Work Area**: 1033.6mm x 631.3mm
- **Z Range**: -199.9mm to -0.1mm
- **USB**: VID_1CBE PID_0002 on COM3
- **Connection**: Direct USB to MiniPC_103
- **Capabilities**: PrintAndCut, MoveXY, MoveZ, Vision, DashedPattern, JobTimeEstimation, SafeOperationMode, CutBezier

## Troubleshooting

### Device Setup (First Time)

If `PlotterProcess` shows as Down with `NoDeviceSelectedInConfig`:

1. Verify the laser is connected: `./tunnel.sh exec "wmic path Win32_PnPEntity where \"Caption like '%USB%'\" get Caption,DeviceID,Status /format:csv"`
2. Verify cloud config: POST to `/api/Proxy/VerifyCloudDeviceConfig?serialNo=Q42-3066`
3. Add the device: POST to `/api/Proxy/AddDevice?serialNo=Q42-3066&modelId=Q400_RF&deviceConfigSource=TrotecSettings&machineLayer=Plotter`
   - This downloads factory calibration from Trotec cloud — can take several minutes on slow connections
4. Check processes: GET `/api/Diagnostics/GetProcessesState` — PlotterProcess should be Running

### Config Files on Windows

| Path | Purpose |
|------|---------|
| `C:\ProgramData\Trotec\JobDispatcher.ConsoleServer\Config.xml` | Machine model config |
| `C:\ProgramData\Trotec\MachineLayer.Configuration\` | Device calibration data |
| `C:\ProgramData\Trotec\JobDispatcher.ConsoleServer\log_ML.init.log` | PlotterProcess startup log |
| `C:\Program Files (x86)\Trotec\Ruby\` | Ruby installation |
| `C:\Program Files (x86)\Trotec\Ruby\JobDispatcher\Options\AllMachineConfigurations.json` | All supported models |

## License

Private - project-shamrock
