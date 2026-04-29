#!/usr/bin/env python3
"""Trotec Ruby API client for controlling the Q400 laser over SSH tunnel."""

import json
import os
import sys
import urllib3
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# Suppress SSL warnings for self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = "https://localhost:5001"
DEVICE_SN = os.getenv("RUBY_DEVICE_SN", "Q42-3066")
API_VERSION = "1.0-OpenApi"


class RubyClient:
    def __init__(self, email=None, password=None):
        email = email or os.getenv("RUBY_EMAIL")
        password = password or os.getenv("RUBY_PASSWORD")
        if not email or not password:
            raise ValueError("Set RUBY_EMAIL and RUBY_PASSWORD in .env or pass as args")
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "Accept": "application/json",
            "x-target-device": DEVICE_SN,
        })
        self.token = None

    def sign_in(self):
        """Authenticate and store JWT token."""
        resp = self.session.post(f"{API_BASE}/api/User/SignIn", json={
            "email": self.email,
            "password": self.password,
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data["token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        print(f"Signed in as {data['name']} ({data['email']}) role={data['roles']}")
        return data

    def generate_pat(self):
        """Generate a PersonalAccessToken for OpenAPI endpoints."""
        resp = self.session.post(f"{API_BASE}/api/User/GeneratePersonalAccessToken")
        resp.raise_for_status()
        pat = resp.json()
        print(f"PAT generated (expires far future)")
        return pat

    # --- Device info ---

    def get_device_status(self):
        """Get laser device status via OpenAPI."""
        resp = self.session.get(f"{API_BASE}/api/OpenApi/GetDeviceStatus",
                                headers={"x-api-version": API_VERSION})
        if not resp.content:
            return {"status": "unknown", "note": "empty response"}
        return resp.json()

    def list_devices(self):
        """List all connected devices."""
        resp = self.session.get(f"{API_BASE}/api/Proxy/ListDevices")
        if not resp.content:
            return []
        return resp.json()

    def get_processes(self):
        """Get Ruby service process states."""
        resp = self.session.get(f"{API_BASE}/api/Diagnostics/GetProcessesState")
        if not resp.content:
            return []
        return resp.json()

    def get_version(self):
        """Get Ruby software version info."""
        resp = self.session.get(f"{API_BASE}/api/Info/GetVersionInfo")
        if not resp.content:
            return {}
        return resp.json()

    # --- Designs & Workbenches ---

    def get_designs(self):
        """List uploaded designs."""
        resp = self.session.get(f"{API_BASE}/api/OpenApi/GetDesigns",
                                headers={"x-api-version": API_VERSION})
        if not resp.content:
            return []
        return resp.json()

    def get_workbenches(self):
        """List workbenches."""
        resp = self.session.get(f"{API_BASE}/api/OpenApi/GetWorkbenches",
                                headers={"x-api-version": API_VERSION})
        if not resp.content:
            return []
        return resp.json()

    def get_designs_internal(self):
        """List designs via internal API (more detail)."""
        resp = self.session.get(f"{API_BASE}/api/DesignData/GetDesigns")
        if not resp.content:
            return []
        return resp.json()

    def get_workbenches_internal(self):
        """List workbenches via internal API (more detail)."""
        resp = self.session.get(f"{API_BASE}/api/Workbench/GetWorkbenches")
        if not resp.content:
            return []
        return resp.json()

    # --- File Upload ---

    def upload_file(self, filepath):
        """Upload a design file (SVG, PDF, etc) to Ruby."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        print(f"Uploading {filepath.name} ({filepath.stat().st_size} bytes)...")

        with open(filepath, "rb") as f:
            resp = self.session.post(
                f"{API_BASE}/api/FileUpload/Upload",
                files={"uploadedFile": (filepath.name, f)},
                timeout=60,
            )

        result = resp.json() if resp.content else {}
        if resp.status_code == 200 and "code" not in result:
            print(f"Upload successful!")
        else:
            print(f"Upload response ({resp.status_code}): {result}")

        return result

    def upload_file_openapi(self, filepath, import_profile_id=None):
        """Upload via OpenAPI endpoint (needs PAT auth)."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        pat = self.generate_pat()
        headers = {
            "Authorization": f"PersonalAccessToken {pat}",
            "x-api-version": API_VERSION,
        }
        params = {}
        if import_profile_id:
            params["importProfileId"] = import_profile_id

        print(f"Uploading {filepath.name} via OpenAPI...")
        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{API_BASE}/api/OpenApi/Upload",
                files={"uploadedFile": (filepath.name, f)},
                headers=headers,
                params=params,
                verify=False,
                timeout=60,
            )

        result = resp.json() if resp.content else {}
        print(f"OpenAPI upload response ({resp.status_code}): {result}")
        return result

    # --- Queue ---

    def get_queue(self):
        """Get queue state."""
        resp = self.session.get(f"{API_BASE}/api/Queue/GetQueue",
                                params={"deviceSn": DEVICE_SN})
        if not resp.content:
            return {"entries": [], "note": "empty response"}
        return resp.json()

    def enqueue_workbench(self, workbench_id):
        """Add a workbench to the queue."""
        resp = self.session.post(
            f"{API_BASE}/api/OpenApi/EnqueueWorkbench",
            headers={"x-api-version": API_VERSION},
            params={"workbenchId": workbench_id},
        )
        return resp.json()

    def acknowledge_issues(self, issue_ids):
        """Acknowledge device issues to clear paused state."""
        resp = self.session.post(
            f"{API_BASE}/api/Queue/AcknowledgeIssues",
            params={"deviceSn": DEVICE_SN},
            json=issue_ids,
        )
        return resp.json() if resp.content else {}

    def resume_queue(self):
        """Resume the queue after pause."""
        resp = self.session.post(f"{API_BASE}/api/Queue/Resume",
                                  params={"deviceSn": DEVICE_SN})
        return resp.json() if resp.content else {}

    def run_queue(self):
        """Start processing the queue."""
        resp = self.session.post(f"{API_BASE}/api/Queue/RunQueue",
                                  params={"deviceSn": DEVICE_SN})
        return resp.json() if resp.content else {}

    def stop_queue(self):
        """Stop the queue."""
        resp = self.session.post(f"{API_BASE}/api/Queue/Stop",
                                  params={"deviceSn": DEVICE_SN})
        return resp.json() if resp.content else {}

    # --- Device Control ---

    def move_z(self, z_mm):
        """Move Z stage to absolute position (mm, negative = down)."""
        resp = self.session.put(f"{API_BASE}/api/Device/MoveZ",
                                params={"z": z_mm})
        return resp.json() if resp.content else {}

    def empty_move(self, x=None, y=None, z=None):
        """Move head/table without a job."""
        params = {}
        if x is not None:
            params["x"] = x
        if y is not None:
            params["y"] = y
        if z is not None:
            params["z"] = z
        resp = self.session.put(f"{API_BASE}/api/Device/EmptyMove", params=params)
        return resp.json() if resp.content else {}

    # --- Convenience ---

    def full_status(self):
        """Print a comprehensive status report."""
        print("=" * 60)
        print("TROTEC Q400 LASER STATUS")
        print("=" * 60)

        print("\n--- Device ---")
        status = self.get_device_status()
        print(f"  Model:    {status.get('model', 'unknown')}")
        print(f"  Serial:   {status.get('serialNo', 'unknown')}")
        print(f"  Status:   {status.get('status', 'unknown')}")
        print(f"  Rotary:   {status.get('attachedRotary', 'None')}")
        if status.get("jobName"):
            print(f"  Job:      {status['jobName']}")
            print(f"  Progress: {status['progress']:.1f}%")
            print(f"  Remaining: {status['remainingTime']:.0f}s")
        issues = status.get("issues", [])
        if issues:
            print(f"  Issues ({len(issues)}):")
            for issue in issues:
                active = "ACTIVE" if issue.get("active") else "resolved"
                print(f"    [{active}] {issue['code']} ({issue['severity']})")

        print("\n--- Processes ---")
        for p in self.get_processes():
            err = ""
            if "processError" in p:
                err = f" -> {p['processError'].get('message', str(p['processError']))}"
            icon = "●" if p["processState"] == "Running" else "○"
            print(f"  {icon} {p['processState']:8s} {p['processName']}{err}")

        print("\n--- Designs ---")
        designs = self.get_designs()
        if isinstance(designs, list):
            print(f"  {len(designs)} design(s)")
            for d in designs[:5]:
                print(f"    - {d.get('name', d.get('id', 'unknown'))}")
        else:
            print(f"  {designs}")

        print("\n--- Queue ---")
        queue = self.get_queue()
        if isinstance(queue, dict) and "entries" in queue:
            print(f"  {len(queue['entries'])} item(s) in queue")
        else:
            print(f"  {queue}")

        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: ruby_client.py <command> [args]")
        print("Commands: status, upload <file>, designs, workbenches, queue,")
        print("          move-z <mm>, processes, version, resume, acknowledge,")
        print("          logs [ml|nc|issues|api|status] [lines]")
        return

    client = RubyClient()
    client.sign_in()

    cmd = sys.argv[1]

    if cmd == "status":
        client.full_status()
    elif cmd == "upload":
        if len(sys.argv) < 3:
            print("Usage: ruby_client.py upload <file>")
            return
        result = client.upload_file(sys.argv[2])
        if isinstance(result, dict) and "code" in result:
            print("Trying OpenAPI upload as fallback...")
            client.upload_file_openapi(sys.argv[2])
    elif cmd == "designs":
        print(json.dumps(client.get_designs(), indent=2))
    elif cmd == "workbenches":
        print(json.dumps(client.get_workbenches(), indent=2))
    elif cmd == "queue":
        print(json.dumps(client.get_queue(), indent=2))
    elif cmd == "move-z":
        if len(sys.argv) < 3:
            print("Usage: ruby_client.py move-z <mm>")
            return
        print(client.move_z(float(sys.argv[2])))
    elif cmd == "processes":
        for p in client.get_processes():
            err = ""
            if "processError" in p:
                err = f" -> {p['processError'].get('message', str(p['processError']))}"
            icon = "●" if p["processState"] == "Running" else "○"
            print(f"  {icon} {p['processState']:8s} {p['processName']}{err}")
    elif cmd == "version":
        print(json.dumps(client.get_version(), indent=2))
    elif cmd == "resume":
        print(client.resume_queue())
    elif cmd == "acknowledge":
        status = client.get_device_status()
        issues = status.get("issues", [])
        if issues:
            ids = [i["id"] for i in issues]
            print(f"Acknowledging {len(ids)} issue(s)...")
            print(client.acknowledge_issues(ids))
        else:
            print("No issues to acknowledge")
    elif cmd == "logs":
        import subprocess
        log_files = {
            "ml": "log_ML.log",
            "nc": "log_ML.nc.log",
            "issues": "log_Issues.log",
            "api": "log_Api.log",
            "status": "log_StatusD.log",
        }
        which = sys.argv[2] if len(sys.argv) > 2 else "ml"
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        if which not in log_files:
            print(f"Available logs: {', '.join(log_files.keys())}")
            return
        log_path = f"C:\\ProgramData\\Trotec\\JobDispatcher.ConsoleServer\\{log_files[which]}"
        result = subprocess.run(
            ["ssh", "trotec", f'powershell -Command "Get-Content \'{log_path}\' -Tail {lines}"'],
            capture_output=True, text=True, timeout=30,
        )
        print(result.stdout)
        if result.stderr and "WARNING" not in result.stderr:
            print(result.stderr)
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
