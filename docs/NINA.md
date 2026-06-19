# NINA critical-reserve safety (ASCOM Alpaca)

When an astro rig runs off a field battery, this app can tell NINA to park the
mount, warm the camera, and disconnect before the pack dies — via an embedded
**ASCOM Alpaca SafetyMonitor** (local HTTP, loopback-only).

## 1. Enable in the app
Settings → **Astro (ASCOM Alpaca SafetyMonitor)** → enable, port `11111` → Apply.
Also set **Critical-SOC** and **Fail-safe timeout** under *Critical-reserve safety*.
Check it's up:
```
curl http://127.0.0.1:11111/api/v1/safetymonitor/0/issafe
```

## 2. Add it in NINA
Equipment → **Safety Monitor** → ASCOM/Alpaca → add a device at `127.0.0.1:11111`,
device number `0` (or discover) → Connect.

## 3. Advanced Sequencer
Add a **Safety Monitor** trigger → *on unsafe*: Park mount → Warm camera →
Disconnect equipment → (optional) Shutdown.

## Trip logic
- **SAFE** while SOC ≥ critical, or while charging (external power present).
- **UNSAFE** when SOC < critical and on battery (latched); recovery needs the
  recover-SOC **and** charging (hysteresis — no flapping).
- A brief BLE dropout holds the last state; data older than the fail-safe timeout
  (or never received) → **UNSAFE** (stale = unsafe; the gear is the priority).

## Single-client BLE
The pack accepts one BLE client at a time — close other apps (vendor app, other
tools) connected to that battery before connecting here.
