import streamlit as st
import requests
import pandas as pd
import os
import json
from history import log_task, HISTORY_FILE

AGENT_KEY = "super-secret-fleet-key-123"
headers = {"X-API-KEY": AGENT_KEY}
INVENTORY_FILE = "inventory.json"

st.set_page_config(page_title="Fleet Manager", layout="wide")

# --- 1. Inventory Management Helper Functions ---
def load_inventory():
    """Loads the fleet list from disk."""
    if os.path.exists(INVENTORY_FILE):
        try:
            with open(INVENTORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_inventory(data):
    """Saves the current fleet list to disk."""
    with open(INVENTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize session state from the JSON file
if 'fleet_data' not in st.session_state:
    st.session_state.fleet_data = load_inventory()

# --- 2. Sidebar: Add New Host ---
st.sidebar.header("➕ Add New Host")
with st.sidebar.form("add_host_form", clear_on_submit=True):
    new_ip = st.text_input("IP Address or Hostname", placeholder="192.168.1.100")
    new_port = st.text_input("Port", value="8080")
    submitted = st.form_submit_button("Add to Fleet")
    
    if submitted:
        if new_ip:
            # Generate a simple ID
            new_id = max([h.get('id', 0) for h in st.session_state.fleet_data], default=0) + 1
            new_host = {"id": new_id, "ip": new_ip, "port": new_port, "status": "Unknown"}
            
            st.session_state.fleet_data.append(new_host)
            save_inventory(st.session_state.fleet_data)
            st.sidebar.success(f"Added {new_ip}")
            st.rerun()
        else:
            st.sidebar.error("IP Address is required.")

# --- 3. Main UI ---
tab1, tab2 = st.tabs(["🎛️ Dashboard", "📜 Task History"])

with tab1:
    st.title("🛰️ Agent-Based Fleet Manager")
    
    if not st.session_state.fleet_data:
        st.info("Your fleet is empty. Add a host using the sidebar on the left.")
    
    for i, machine in enumerate(st.session_state.fleet_data):
        # Added an extra column for the Remove button
        col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
        
        agent_url = f"http://{machine['ip']}:{machine['port']}"
        col1.write(f"**Host:** {machine['ip']}")
        col2.write(f"**Status:** {machine['status']}")
        
        if col3.button("Health", key=f"health_{i}"):
            try:
                resp = requests.get(f"{agent_url}/status", headers=headers, timeout=5)
                if resp.status_code == 200:
                    st.session_state.fleet_data[i]['status'] = "Online"
                    save_inventory(st.session_state.fleet_data)
                    st.success("Online")
                else:
                    st.error("Auth Failed")
            except:
                st.session_state.fleet_data[i]['status'] = "Offline"
                save_inventory(st.session_state.fleet_data)
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
                
        # NEW: Remove Host Button
        if col6.button("❌ Remove", key=f"del_{i}"):
            st.session_state.fleet_data.pop(i)
            save_inventory(st.session_state.fleet_data)
            st.rerun()

with tab2:
    st.subheader("Recent Activity Log")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                history_data = json.load(f)
                if history_data:
                    st.dataframe(pd.DataFrame(history_data), use_container_width=True)
                    if st.button("Clear History"):
                        os.remove(HISTORY_FILE)
                        st.rerun()
                else:
                    st.info("No tasks recorded yet.")
            except json.JSONDecodeError:
                st.info("History file is empty or corrupted.")
    else:
        st.info("No history found.")