"""Embedded ASCOM Alpaca SafetyMonitor (milestone 5).

A tiny local HTTP server NINA consumes natively (Add device -> Alpaca ->
SafetyMonitor). Exposes the standard Alpaca management + SafetyMonitor API and
answers `issafe` from the injected provider (the FailsafeMonitor). Read-only,
binds 127.0.0.1 by default — never faces the network. (SPEC §6.)
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from aiohttp import web

log = logging.getLogger("ecoworthy_bms.alpaca")

_API = "/api/v1/safetymonitor/0"


class AlpacaSafetyServer:
    def __init__(self, is_safe_provider: Callable[[], bool],
                 host: str = "127.0.0.1", port: int = 11111,
                 device_name: str = "ECO-WORTHY BMS",
                 unique_id: str = "ecoworthy-bms-monitor-safety-0") -> None:
        self._provider = is_safe_provider
        self._host = host
        self._port = int(port)
        self._name = device_name
        self._uid = unique_id
        self._connected = False
        self._stxn = 0
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self.app = self._build_app()

    # -- Alpaca envelope ----------------------------------------------------
    @staticmethod
    def _client_txn(request: web.Request) -> int:
        src = request.query if request.method == "GET" else getattr(request, "_form_cache", {})
        for k, v in src.items():
            if k.lower() == "clienttransactionid":
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return 0
        return 0

    def _env(self, request: web.Request, value=None) -> web.Response:
        self._stxn += 1
        body = {
            "ClientTransactionID": self._client_txn(request),
            "ServerTransactionID": self._stxn,
            "ErrorNumber": 0,
            "ErrorMessage": "",
        }
        if value is not None:
            body["Value"] = value
        return web.json_response(body)

    # -- handlers -----------------------------------------------------------
    async def _apiversions(self, request): return self._env(request, [1])

    async def _description(self, request):
        return self._env(request, {
            "ServerName": "ECO-WORTHY BMS Windows app",
            "Manufacturer": "ecoworthy-bms-monitor (community)",
            "ManufacturerVersion": "0.1",
            "Location": "local",
        })

    async def _configureddevices(self, request):
        return self._env(request, [{
            "DeviceName": self._name,
            "DeviceType": "SafetyMonitor",
            "DeviceNumber": 0,
            "UniqueID": self._uid,
        }])

    async def _issafe(self, request):
        try:
            safe = bool(self._provider())
        except Exception as e:  # noqa: BLE001 — provider failure must read UNSAFE
            log.warning("issafe provider error: %s", e)
            safe = False
        return self._env(request, safe)

    async def _get_connected(self, request): return self._env(request, self._connected)

    async def _put_connected(self, request):
        data = await request.post()
        request._form_cache = data  # for client-txn echo on PUT
        for k, v in data.items():
            if k.lower() == "connected":
                self._connected = str(v).lower() == "true"
        return self._env(request)

    async def _name_h(self, request): return self._env(request, self._name)
    async def _desc_h(self, request): return self._env(request, "ECO-WORTHY BMS critical-reserve safety monitor")
    async def _driverinfo(self, request): return self._env(request, "ecoworthy-bms-monitor embedded Alpaca SafetyMonitor")
    async def _driverversion(self, request): return self._env(request, "0.1")
    async def _interfaceversion(self, request): return self._env(request, 1)
    async def _supportedactions(self, request): return self._env(request, [])

    def _build_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/management/apiversions", self._apiversions)
        app.router.add_get("/management/v1/description", self._description)
        app.router.add_get("/management/v1/configureddevices", self._configureddevices)
        app.router.add_get(f"{_API}/issafe", self._issafe)
        app.router.add_get(f"{_API}/connected", self._get_connected)
        app.router.add_put(f"{_API}/connected", self._put_connected)
        app.router.add_get(f"{_API}/name", self._name_h)
        app.router.add_get(f"{_API}/description", self._desc_h)
        app.router.add_get(f"{_API}/driverinfo", self._driverinfo)
        app.router.add_get(f"{_API}/driverversion", self._driverversion)
        app.router.add_get(f"{_API}/interfaceversion", self._interfaceversion)
        app.router.add_get(f"{_API}/supportedactions", self._supportedactions)
        return app

    # -- lifecycle ----------------------------------------------------------
    async def start(self) -> None:
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        log.info("Alpaca SafetyMonitor on http://%s:%d%s", self._host, self._port, _API)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            self._site = None
