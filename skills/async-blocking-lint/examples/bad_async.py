"""Bad: synchronous IO inside async handlers blocks the event loop."""
import time
import requests
import subprocess


async def get_patient(patient_id: str):
    time.sleep(0.1)
    resp = requests.get(f"https://ehr.example/Patient/{patient_id}")
    return resp.json()


async def export_patient(patient_id: str):
    subprocess.run(["pg_dump", "--table=patient"], check=True)
    return {"status": "exported"}
