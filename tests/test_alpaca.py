import asyncio

from aiohttp.test_utils import TestClient, TestServer

from ecoworthy_bms.safety.alpaca import AlpacaSafetyServer


def test_alpaca_api():
    asyncio.run(_run())


async def _run():
    state = {"safe": True}
    srv = AlpacaSafetyServer(lambda: state["safe"])
    async with TestClient(TestServer(srv.app)) as client:
        r = await client.get("/management/apiversions?ClientTransactionID=7")
        j = await r.json()
        assert j["Value"] == [1] and j["ClientTransactionID"] == 7 and j["ErrorNumber"] == 0

        r = await client.get("/management/v1/configureddevices")
        j = await r.json()
        assert j["Value"][0]["DeviceType"] == "SafetyMonitor"
        assert j["Value"][0]["DeviceNumber"] == 0

        r = await client.get("/api/v1/safetymonitor/0/issafe")
        assert (await r.json())["Value"] is True

        state["safe"] = False
        r = await client.get("/api/v1/safetymonitor/0/issafe")
        assert (await r.json())["Value"] is False

        r = await client.get("/api/v1/safetymonitor/0/interfaceversion")
        assert (await r.json())["Value"] == 1
        r = await client.get("/api/v1/safetymonitor/0/name")
        assert (await r.json())["Value"]

        r = await client.put("/api/v1/safetymonitor/0/connected",
                              data={"Connected": "true", "ClientTransactionID": "3"})
        assert (await r.json())["ErrorNumber"] == 0
        r = await client.get("/api/v1/safetymonitor/0/connected")
        assert (await r.json())["Value"] is True

    # provider failure must read UNSAFE, never crash
    def boom():
        raise RuntimeError("provider down")
    srv2 = AlpacaSafetyServer(boom)
    async with TestClient(TestServer(srv2.app)) as client:
        r = await client.get("/api/v1/safetymonitor/0/issafe")
        assert (await r.json())["Value"] is False
