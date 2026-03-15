import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import streamlit as st
import requests
import pandas as pd
import os
import json
from history import log_task, HISTORY_FILE

AGENT_KEY = "super-secret-fleet-key-123"
headers = {"X-API-KEY": AGENT_KEY}
INVENTORY_FILE = "inventory.json"
# --- 1. Inventory Management Helper Functions ---
def load_inventory():
    """Loads the fleet list from disk and ensures a 'Select' column exists."""
    if os.path.exists(INVENTORY_FILE):
        try:
            with open(INVENTORY_FILE, "r") as f:
                data = json.load(f)
                # Ensure every loaded machine has a Select key defaulting to False
                for item in data:
                    item['Select'] = False 
                return data
        except json.JSONDecodeError:
            return []
    return []

def save_inventory(data):
    """Saves the current fleet list to disk, stripping out the temporary 'Select' state."""
    save_data = [{k: v for k, v in d.items() if k != 'Select'} for d in data]
    with open(INVENTORY_FILE, "w") as f:
        json.dump(save_data, f, indent=4)


st.set_page_config(page_title="Fleet Manager", layout="wide")

# --- 1. Define User Credentials ---
# In production, load this from a secure config.yaml file or database
config = {}
with open('./credentials.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Pre-hashing all plain text passwords once
# stauth.Hasher.hash_passwords(config['credentials'])

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)
# import pdb; pdb.set_trace()
# --- 3. Render the Login Widget ---
authenticator.login("main")

# --- 4. Handle Authentication States ---
if st.session_state.get('authentication_status') == False:
    st.error("Username/password is incorrect")

elif st.session_state.get('authentication_status') == None:
    st.warning("Please enter your username and password")

elif st.session_state.get('authentication_status'):
    # --- USER IS LOGGED IN ---
    # Optional: Add a logout button to the sidebar
    authenticator.logout("Logout", "sidebar")
    name = st.session_state.get("name")
    st.sidebar.write(f"Welcome, *{name}*")
    
    # ==========================================
    # PASTE YOUR EXISTING APP.PY UI LOGIC HERE
    # (The Inventory Loading, Sidebar Form, and Tabs)
    # ==========================================
    
    # Example placeholder:
    st.title("🛰️ Agent-Based Fleet Manager")
    st.success("You are securely authenticated.")
    # --- 3. Main UI ---
    tab1, tab2 = st.tabs(["🎛️ Dashboard", "📜 Task History"])

    with tab1:
        st.title("🛰️ Agent-Based Fleet Manager")
        
        if not st.session_state.fleet_data:
            st.info("Your fleet is empty. Add a host using the sidebar on the left.")
        else:
            # Create an interactive DataFrame
            df = pd.DataFrame(st.session_state.fleet_data)
            
            st.write("### Fleet Inventory")
            # Render the data editor with a checkbox column
            edited_df = st.data_editor(
                df,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", default=False),
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "ip": st.column_config.TextColumn("IP Address", disabled=True),
                    "port": st.column_config.TextColumn("Port", disabled=True),
                    "status": st.column_config.TextColumn("Status", disabled=True)
                },
                disabled=["id", "ip", "port", "status"],
                hide_index=True,
                use_container_width=True
            )
            
            # Sync the edited selection state back to session state
            st.session_state.fleet_data = edited_df.to_dict('records')
            
            # Filter for only the selected hosts
            selected_hosts = [h for h in st.session_state.fleet_data if h.get('Select', False)]
            has_selection = len(selected_hosts) > 0

            # --- BATCH ACTIONS BAR ---
            st.divider()
            st.write("### Batch Actions")
            col1, col2, col3, col4 = st.columns(4)

            # 1. BATCH HEALTH CHECK
            if col1.button("🩺 Check Health", disabled=not has_selection, use_container_width=True):
                with st.status(f"Checking health for {len(selected_hosts)} machines...", expanded=True) as status:
                    for host in selected_hosts:
                        agent_url = f"http://{host['ip']}:{host['port']}"
                        try:
                            resp = requests.get(f"{agent_url}/status", headers=headers, timeout=5)
                            if resp.status_code == 200:
                                host['status'] = "Online"
                                st.write(f"✅ {host['ip']}: Online")
                            else:
                                host['status'] = "Auth Failed"
                                st.write(f"❌ {host['ip']}: Auth Failed")
                        except Exception:
                            host['status'] = "Offline"
                            st.write(f"❌ {host['ip']}: Offline")
                    save_inventory(st.session_state.fleet_data)
                    status.update(label="Health check complete", state="complete", expanded=False)
                st.rerun()

            # 2. BATCH CHECK UPDATES
            if col2.button("🔍 Check Updates", disabled=not has_selection, use_container_width=True):
                with st.status(f"Scanning {len(selected_hosts)} machines for updates...", expanded=True) as status:
                    results = {}
                    for host in selected_hosts:
                        agent_url = f"http://{host['ip']}:{host['port']}"
                        try:
                            resp = requests.get(f"{agent_url}/check_updates", headers=headers, timeout=60)
                            if resp.status_code == 200:
                                data = resp.json()
                                results[host['ip']] = data
                                st.write(f"✅ {host['ip']}: {data['package_count']} updates found.")
                            else:
                                st.write(f"❌ {host['ip']}: Failed to fetch updates.")
                        except Exception:
                            st.write(f"❌ {host['ip']}: Connection Error.")
                    status.update(label="Update scan complete", state="complete", expanded=False)
                    
                # Display detailed results in expanders after the status block closes
                if results:
                    st.write("#### Update Details")
                    for ip, data in results.items():
                        if data['package_count'] > 0:
                            with st.expander(f"{ip} ({data['package_count']} packages)"):
                                st.code(data['output'])

            # 3. BATCH PATCH
            if col3.button("🚀 Deploy Patches", disabled=not has_selection, use_container_width=True, type="primary"):
                with st.status(f"Patching {len(selected_hosts)} machines...", expanded=True) as status:
                    for host in selected_hosts:
                        agent_url = f"http://{host['ip']}:{host['port']}"
                        st.write(f"Patching {host['ip']}...")
                        try:
                            resp = requests.post(f"{agent_url}/upgrade", headers=headers, timeout=300)
                            if resp.status_code == 200:
                                st.write(f"✅ {host['ip']}: Successfully Patched!")
                                log_task(host['ip'], "N/A", "Batch Patch", "Success", resp.json().get("output", ""))
                            else:
                                st.write(f"❌ {host['ip']}: Patching Failed.")
                                log_task(host['ip'], "N/A", "Batch Patch", "Failed", resp.text) 
                        except Exception as e:
                            st.write(f"❌ {host['ip']}: Error ({e}).")
                            log_task(host['ip'], "N/A", "Batch Patch", "Error", str(e))
                    status.update(label="Patching cycle complete", state="complete", expanded=False)

            # 4. BATCH REMOVE
            if col4.button("🗑️ Remove Selected", disabled=not has_selection, use_container_width=True):
                # Keep only hosts that are NOT selected
                st.session_state.fleet_data = [h for h in st.session_state.fleet_data if not h.get('Select', False)]
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
                new_id = max([h.get('id', 0) for h in st.session_state.fleet_data], default=0) + 1
                new_host = {"Select": False, "id": new_id, "ip": new_ip, "port": new_port, "status": "Unknown"}
                st.session_state.fleet_data.append(new_host)
                save_inventory(st.session_state.fleet_data)
                st.sidebar.success(f"Added {new_ip}")
                st.rerun()
            else:
                st.sidebar.error("IP Address is required.")



