#!/usr/bin/python3
"""GPU waybar module — NVIDIA GTX 1650 Ti via NVML ctypes."""
import json, ctypes, ctypes.util

# ── NVML structs ──────────────────────────────────────────────────────────────
class NvmlUtilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

class NvmlMemory(ctypes.Structure):
    _fields_ = [("total", ctypes.c_ulonglong),
                ("free",  ctypes.c_ulonglong),
                ("used",  ctypes.c_ulonglong)]

NVML_SUCCESS           = 0
NVML_TEMPERATURE_GPU   = 0
NVML_CLOCK_GRAPHICS    = 0
NVML_CLOCK_MEM         = 2

def query():
    nvml = ctypes.CDLL("libnvidia-ml.so.1")
    if nvml.nvmlInit_v2() != NVML_SUCCESS:
        raise RuntimeError("nvmlInit failed")

    handle = ctypes.c_void_p()
    nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle))

    # Name
    name_buf = ctypes.create_string_buffer(96)
    nvml.nvmlDeviceGetName(handle, name_buf, 96)
    name = name_buf.value.decode()

    # Utilization
    util = NvmlUtilization()
    nvml.nvmlDeviceGetUtilizationRates(handle, ctypes.byref(util))
    gpu_pct = util.gpu

    # Encoder / decoder
    enc, enc_p = ctypes.c_uint(0), ctypes.c_uint(0)
    dec, dec_p = ctypes.c_uint(0), ctypes.c_uint(0)
    nvml.nvmlDeviceGetEncoderUtilization(handle, ctypes.byref(enc), ctypes.byref(enc_p))
    nvml.nvmlDeviceGetDecoderUtilization(handle, ctypes.byref(dec), ctypes.byref(dec_p))

    # Temperature
    temp = ctypes.c_uint(0)
    nvml.nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU, ctypes.byref(temp))

    # Power draw (supported on GTX 1650 Ti)
    power_mw = ctypes.c_uint(0)
    r_pwr = nvml.nvmlDeviceGetPowerUsage(handle, ctypes.byref(power_mw))
    power_w = power_mw.value / 1000.0 if r_pwr == NVML_SUCCESS else None

    # VRAM
    mem = NvmlMemory()
    nvml.nvmlDeviceGetMemoryInfo(handle, ctypes.byref(mem))
    vram_used  = mem.used  / (1024 ** 2)   # bytes → MiB
    vram_total = mem.total / (1024 ** 2)

    # Clock speeds
    core_mhz, mem_mhz = ctypes.c_uint(0), ctypes.c_uint(0)
    nvml.nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS, ctypes.byref(core_mhz))
    nvml.nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM,      ctypes.byref(mem_mhz))

    nvml.nvmlShutdown()

    return {
        "name":       name,
        "gpu_pct":    gpu_pct,
        "enc_pct":    enc.value,
        "dec_pct":    dec.value,
        "temp":       temp.value,
        "power_w":    power_w,
        "vram_used":  vram_used,
        "vram_total": vram_total,
        "core_mhz":   core_mhz.value,
        "mem_mhz":    mem_mhz.value,
    }

# ── main ──────────────────────────────────────────────────────────────────────
try:
    m = query()

    vu_g = m["vram_used"]  / 1024
    vt_g = m["vram_total"] / 1024
    pwr  = f"{m['power_w']:.1f}W" if m["power_w"] is not None else "N/A"

    lines = [
        m["name"],
        "",
        f"  Usage:     {m['gpu_pct']}%",
        f"  Encoder:   {m['enc_pct']}%",
        f"  Decoder:   {m['dec_pct']}%",
        "",
        f"  Temp:      {m['temp']}°C",
        f"  Power:     {pwr}",
        "",
        f"  VRAM:      {vu_g:.1f}G  /  {vt_g:.1f}G",
        f"  Core:      {m['core_mhz']} MHz",
        f"  Memory:    {m['mem_mhz']} MHz",
    ]

    css = "critical" if m["gpu_pct"] > 85 else ("warning" if m["gpu_pct"] > 70 else "")

    print(json.dumps({
        "text":    f"󰾲  {m['gpu_pct']}%",
        "tooltip": "\n".join(lines),
        "class":   css,
    }))

except Exception as e:
    print(json.dumps({
        "text":    "󰾲  N/A",
        "tooltip": f"GPU unavailable\n  {e}",
        "class":   "",
    }))
