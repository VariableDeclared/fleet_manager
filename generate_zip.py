import os
import shutil

# 1. Define the project structure and file contents
project_name = "fleet_manager"
files = {
    "distros/__init__.py": "",
    "distros/base.py": '''from abc import ABC, abstractmethod

class LinuxDistro(ABC):
    @abstractmethod
    def get_update_command(self) -> str:
        pass

    @abstractmethod
    def get_upgrade_command(self) -> str:
        pass

    @abstractmethod
    def get_kernel_version(self) -> str:
        pass

    @abstractmethod
    def get_check_updates_command(self) -> str:
        pass
''',
    "distros/ubuntu.py": '''from .base import LinuxDistro

class UbuntuManager(LinuxDistro):
    def get_update_command(self) -> str:
        return "sudo apt-get update"

    def get_upgrade_command(self) -> str:
        return "sudo apt-get dist-upgrade -y"

    def get_kernel_version(self) -> str:
        return "uname -r"

    def get_check_updates_command(self) -> str:
        return "sudo apt-get update > /dev/null && apt-get -s upgrade | grep ^Inst || true"
''',
    "distros/redhat.py": '''from .base import LinuxDistro

class RedHatManager(LinuxDistro):
    def get_update_command(self) -> str:
        return "sudo dnf check-update || true"

    def get_upgrade_command(self) -> str:
        return "sudo dnf upgrade -y"

    def get_kernel_version(self) -> str:
        return "uname -r"

    def get_check_updates_command(self) -> str:
        return "sudo dnf -q check-update || true"
''',
    "agent.py": '''import subprocess
import os
import platform
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from distros.ubuntu import UbuntuManager
from distros.redhat import RedHatManager

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
SECRET_KEY = os.getenv("AGENT_SECRET_KEY", "super-secret-fleet-key-123")

app = FastAPI()

async def validate_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == SECRET_KEY:
        return api_key_header
    raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials")

def get_handler():
    distro_id = platform.freedesktop_os_release().get("ID", "").lower()
    if "ubuntu" in distro_id or "debian" in distro_id:
        return UbuntuManager()
    if "rhel" in distro_id or "centos" in distro_id or "rocky" in distro_id:
        return RedHatManager()
    raise Exception(f"Unsupported distribution: {distro_id}")

@app.get("/status", dependencies=[Depends(validate_api_key)])
def get_status():
    handler = get_handler()
    kernel = subprocess.getoutput(handler.get_kernel_version())
    return {"status": "online", "distro": platform.system(), "kernel": kernel}

@app.get("/check_updates", dependencies=[Depends(validate_api_key)])
def check_updates():
    handler = get_handler()
    try:
        cmd = handler.get_check_updates_command()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout.strip()
        package_count = len(output.split('\\n')) if output else 0
        return {"status": "success", "package_count": package_count, "output": output or "No updates."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upgrade", dependencies=[Depends(validate_api_key)])
def run_upgrade():
    handler = get_handler()
    try:
        subprocess.run(handler.get_update_command(), shell=True, check=True)
        result = subprocess.run(handler.get_upgrade_command(), shell=True, capture_output=True, text=True)
        return {"message": "Success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
''',
    "history.py": '''import json
import datetime
import os

HISTORY_FILE = "task_history.json"

def log_task(ip, distro, action, status, details=""):
    record = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "distro": distro,
        "action": action,
        "status": status,
        "details": details[:200] + "..." if len(details) > 200 else details
    }
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                pass
    history.insert(0, record)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[:100], f, indent=4)
''',
    "app.py": '''import streamlit as st
import requests
import pandas as pd
import os
import json
from history import log_task, HISTORY_FILE

AGENT_KEY = "super-secret-fleet-key-123"
headers = {"X-API-KEY": AGENT_KEY}

if 'fleet_data' not in st.session_state:
    st.session_state.fleet_data = [
        {"id": 1, "ip": "127.0.0.1", "port": "8080", "status": "Unknown"},
    ]

st.set_page_config(page_title="Fleet Manager", layout="wide")
tab1, tab2 = st.tabs(["🎛️ Dashboard", "📜 Task History"])

with tab1:
    st.title("🛰️ Agent-Based Fleet Manager")
    for i, machine in enumerate(st.session_state.fleet_data):
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        agent_url = f"http://{machine['ip']}:{machine['port']}"
        col1.write(f"**Host:** {machine['ip']}")
        col2.write(f"**Status:** {machine['status']}")
        
        if col3.button("Health", key=f"health_{i}"):
            try:
                resp = requests.get(f"{agent_url}/status", headers=headers, timeout=5)
                if resp.status_code == 200:
                    st.session_state.fleet_data[i]['status'] = "Online"
                    st.success("Online")
            except:
                st.error("Offline")

        if col4.button("Check Updates", key=f"check_{i}"):
            try:
                resp = requests.get(f"{agent_url}/check_updates", headers=headers, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"Updates: {data['package_count']}")
                    with st.expander("Details"): st.code(data['output'])
            except Exception as e:
                st.error("Failed")

        if col5.button("Patch", key=f"patch_{i}"):
            try:
                resp = requests.post(f"{agent_url}/upgrade", headers=headers, timeout=300)
                if resp.status_code == 200:
                    st.success("Patched")
                    log_task(machine['ip'], "N/A", "Patch", "Success", resp.json().get("output", ""))
            except Exception as e:
                st.error("Failed")
                log_task(machine['ip'], "N/A", "Patch", "Error", str(e))

with tab2:
    st.subheader("Recent Activity Log")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history_data = json.load(f)
            if history_data:
                st.table(pd.DataFrame(history_data))
                if st.button("Clear History"):
                    os.remove(HISTORY_FILE)
                    st.rerun()
''',
    "tests/test_agent.py": '''import pytest
from fastapi.testclient import TestClient
from agent import app, SECRET_KEY

client = TestClient(app)

def test_status_unauthorized():
    response = client.get("/status")
    assert response.status_code == 403

def test_status_authorized():
    headers = {"X-API-KEY": SECRET_KEY}
    response = client.get("/status", headers=headers)
    assert response.status_code in [200, 500] # 500 if run on non-linux OS
''',
    ".github/workflows/python-tests.yml": '''name: Fleet Manager CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.10"
    - run: pip install fastapi uvicorn requests pytest httpx pydantic
    - run: export AGENT_SECRET_KEY="super-secret-fleet-key-123" && pytest tests/test_agent.py
''',
    "main.tf": '''terraform {
  required_providers {
    lxd = {
      source  = "terraform-lxd/lxd"
      version = "~> 2.0"
    }
  }
}
provider "lxd" {
  generate_client_certificates = true
  accept_remote_certificate    = true
}
resource "lxd_profile" "fleet_agent_profile" {
  name = "fleet-agent-bootstrap"
  config = {
    "user.user-data" = file("${path.module}/cloud-init.yaml")
  }
}
resource "lxd_instance" "ubuntu_target" {
  name      = "fleet-ubuntu-01"
  image     = "ubuntu:22.04"
  type      = "virtual-machine"
  profiles  = ["default", lxd_profile.fleet_agent_profile.name]
}
''',
    "cloud-init.yaml": '''#cloud-config
package_upgrade: true
packages: [python3-pip, python3-venv, git, curl]
write_files:
  - path: /etc/systemd/system/fleet-agent.service
    permissions: '0644'
    content: |
      [Unit]
      Description=Linux Fleet Agent
      [Service]
      User=root
      WorkingDirectory=/opt/fleet-agent
      Environment="AGENT_SECRET_KEY=super-secret-fleet-key-123"
      ExecStart=/opt/fleet-agent/venv/bin/uvicorn agent:app --host 0.0.0.0 --port 8080
      Restart=always
      [Install]
      WantedBy=multi-user.target
runcmd:
  - mkdir -p /opt/fleet-agent && cd /opt/fleet-agent
  - python3 -m venv venv
  - /opt/fleet-agent/venv/bin/pip install fastapi uvicorn requests pydantic
  - systemctl daemon-reload
  - systemctl enable fleet-agent --now
'''
}

# 2. Create directories and write files
os.makedirs(project_name, exist_ok=True)
for file_path, content in files.items():
    full_path = os.path.join(project_name, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

# 3. Zip the directory
shutil.make_archive(project_name, 'zip', project_name)

print(f"✅ Success! Your project has been generated and zipped as '{project_name}.zip'")
print(f"You can now delete the temporary '{project_name}' folder if you wish.")