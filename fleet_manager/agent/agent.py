import subprocess
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
        package_count = len(output.split('\n')) if output else 0
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
