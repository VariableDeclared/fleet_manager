import streamlit as st
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
