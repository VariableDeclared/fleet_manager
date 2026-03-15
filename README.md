# 🛰️ Linux Fleet Manager
A modular, agent-based orchestration tool designed to manage, monitor, and patch fleets of Linux machines from a centralized Web UI.

This project replaces insecure, centralized SSH loops with a lightweight, secure HTTP agent running on each target node. It currently supports Debian/Ubuntu (apt) and RHEL/Rocky Linux (dnf) systems, with an extensible architecture to easily add more distributions.

## 🏗️ Architecture
The Orchestrator (Web UI): A responsive Streamlit web application that serves as your control plane. It maintains a dynamic inventory, triggers batch actions, and logs task history.

The Agent (Target Hosts): A lightweight FastAPI application running as a systemd service on each managed Linux machine. It listens for authenticated HTTP requests and executes local package manager commands.

Communication: All communication between the UI and the Agents is secured via an X-API-KEY header.

## ✨ Features
Dynamic Inventory: Add and remove hosts dynamically directly from the UI.

Batch Operations: Select multiple machines to check health, scan for updates, or deploy patches simultaneously.

Pre-flight Checks: View exactly which packages are staged for an upgrade before committing to a patch cycle.

Task Auditing: Automatically logs all actions (Success, Failed, Error) with timestamps and standard output details to a persistent history file.

Modular Design: Easily extend support to Arch, Alpine, or SUSE by adding a new class that inherits from LinuxDistro.

## 🚀 Getting Started
1. Prerequisites
Manager/UI Node: Python 3.10+

Target Nodes: Python 3.10+, pip, venv

2. Setting up the Web UI (Orchestrator)
Clone the repository and install the UI dependencies:

```
git clone https://github.com/your-org/fleet-manager.git
cd fleet-manager
pip install -r requirements.txt
```

Set your secure API key as an environment variable (this must match the key used by your agents):

```
export AGENT_SECRET_KEY="your-secure-api-key"
```

Start the Streamlit dashboard:

```
streamlit run app.py
```

3. Deploying the Agent (Target Nodes)
The agent needs to be running on every machine you want to manage.

Manual Installation:
Copy agent.py and the distros/ folder to your target machine, install FastAPI and Uvicorn, and run the server:

```
pip install fastapi uvicorn requests
export AGENT_SECRET_KEY="your-secure-api-key"
uvicorn agent:app --host 0.0.0.0 --port 8080
(For production, wrap this in a systemd service file as detailed in the deployment documentation).
```

## 🧪 Testing and Development
Unit Tests
The project includes a pytest suite to verify API routing, authentication, and distribution detection.

```
pip install pytest httpx
export AGENT_SECRET_KEY="test-key"
pytest tests/
```

Infrastructure as Code (Test Environment)
You can quickly spin up an ephemeral test fleet using the provided Terraform configuration. This requires a local LXD installation.


### Initializes the LXD provider
```
terraform init
```
### Provisions 1 Ubuntu VM and installs the agent via cloud-init
terraform apply
Once provisioned, Terraform will output the IP addresses of your new test VMs. Add these IPs and port 8080 to your Streamlit UI to begin testing.

## 🔒 Security Hardening
Before deploying this to a production environment, please review the following security checklist:

Web UI Authentication: The UI currently relies on streamlit-authenticator. Ensure default passwords are changed and hashed properly.

Transport Layer Security: The agent communicates over HTTP. In production, place the agent behind a reverse proxy (like Nginx) to enforce HTTPS/TLS.

Principle of Least Privilege: Do not run the agent as root. Run the agent under a dedicated service account and configure /etc/sudoers to allow passwordless execution only for specific package manager commands (apt-get update, dnf upgrade, etc.).