"""Good: async equivalents throughout, with one intentional threadpool offload."""
import asyncio
import httpx


async def get_patient(patient_id: str):
    await asyncio.sleep(0.1)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://ehr.example/Patient/{patient_id}")
    return resp.json()


async def export_patient(patient_id: str):
    # Use asyncio.create_subprocess_exec for shell-out
    proc = await asyncio.create_subprocess_exec(
        "pg_dump", "--table=patient",
        stdout=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    return {"status": "exported"}


async def cpu_bound_in_threadpool():
    """When you genuinely need a sync function, offload to threadpool."""
    import some_legacy_lib
    return await asyncio.to_thread(some_legacy_lib.process, "data")
