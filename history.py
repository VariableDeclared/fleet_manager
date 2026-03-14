import json
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
