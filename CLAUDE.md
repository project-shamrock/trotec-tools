# trotec-tunnel

## What this is
A tunnel/bridge that lets network clients send jobs to a Trotec Q400 RF laser (serial Q42-3066). The laser is controlled by Trotec Ruby software (v2.11.1) on a remote Windows host (MiniPC_103 at 10.160.26.28). SSH tunnels forward the Ruby API ports locally.

## Repo
- GitHub: project-shamrock/trotec-tunnel (private)
- Branch: main

## Tech
- Shell scripts for tunnel management
- Trotec Ruby REST API (HTTPS on ports 5001/2402/5016/etc)
- SSH tunnels for connectivity
- JWT auth via /api/User/SignIn

## Key files
- `tunnel.sh` — tunnel manager (up/down/status/test/ssh/exec)
- `tunnel.config.json` — tunnel port definitions
- `docs/swagger.json` — full OpenAPI spec from Ruby

## Conventions
- All Ruby API calls require HTTPS (self-signed cert, use -k with curl)
- Auth: POST /api/User/SignIn returns JWT, use as Bearer token
- OpenAPI endpoints at /api/OpenApi/*, internal API at /api/*
- Windows commands via `./tunnel.sh exec "<cmd>"` or `ssh trotec "<cmd>"`
