#!/usr/bin/python3
"""CPU waybar module — per-thread usage, per-core temps, load average."""
import json, os, re

STATE_FILE = "/tmp/waybar-cpu-stat"

# ── /proc/stat ────────────────────────────────────────────────────────────────
def read_stat():
    stats = {}
    with open("/proc/stat") as f:
        for line in f:
            if not line.startswith("cpu"):
                break
            parts = line.split()
            vals  = [int(x) for x in parts[1:8]]      # user nice sys idle iowait irq softirq
            total = sum(vals)
            idle  = vals[3] + (vals[4] if len(vals) > 4 else 0)
            stats[parts[0]] = [total, idle]
    return stats

# ── coretemp sysfs ────────────────────────────────────────────────────────────
def read_core_temps():
    """Returns dict {physical_core_index: temp_celsius}."""
    temps = {}
    base  = "/sys/class/hwmon"
    try:
        for hwmon in os.listdir(base):
            path = os.path.join(base, hwmon)
            try:
                with open(os.path.join(path, "name")) as f:
                    if f.read().strip() != "coretemp":
                        continue
            except OSError:
                continue
            for fname in sorted(os.listdir(path)):
                if not fname.endswith("_label"):
                    continue
                stem = fname[:-6]                       # e.g. "temp2"
                try:
                    with open(os.path.join(path, fname)) as lf:
                        label = lf.read().strip()
                    m = re.match(r"Core\s+(\d+)", label)
                    if not m:
                        continue
                    core = int(m.group(1))
                    with open(os.path.join(path, stem + "_input")) as vf:
                        temps[core] = int(vf.read().strip()) // 1000   # m°C → °C
                except OSError:
                    continue
    except OSError:
        pass
    return temps

# ── /proc/loadavg ─────────────────────────────────────────────────────────────
def read_load():
    with open("/proc/loadavg") as f:
        p = f.read().split()
    return float(p[0]), float(p[1]), float(p[2])

# ── delta computation ─────────────────────────────────────────────────────────
current = read_stat()
prev    = {}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE) as f:
            prev = json.load(f)
    except Exception:
        pass
with open(STATE_FILE, "w") as f:
    json.dump(current, f)

usage = {}
for key, (total, idle) in current.items():
    if key in prev:
        dt = total  - prev[key][0]
        di = idle   - prev[key][1]
        usage[key] = max(0.0, min(100.0, (1 - di / dt) * 100)) if dt > 0 else 0.0
    else:
        usage[key] = 0.0

overall = usage.get("cpu", 0.0)
temps   = read_core_temps()
load1, load5, load15 = read_load()

# ── tooltip ───────────────────────────────────────────────────────────────────
# Logical threads sorted; physical core = thread // 2 (Intel HT layout)
threads = sorted(
    [k for k in usage if k != "cpu"],
    key=lambda x: int(x[3:])
)

lines = ["CPU Threads"]
for t in threads:
    n         = int(t[3:])
    phys_core = n // 2
    pct       = usage[t]
    temp_str  = f"   {temps[phys_core]}°C" if phys_core in temps else ""
    lines.append(f"  Thread {n:2d}:  {pct:5.1f}%{temp_str}")

lines += [
    "",
    "Load Average",
    f"  1min:   {load1:.2f}  ·  5min:   {load5:.2f}  ·  15min:  {load15:.2f}",
]

css = "critical" if overall > 85 else ("warning" if overall > 70 else "")

print(json.dumps({
    "text":    f"󰻠  {overall:.0f}%",
    "tooltip": "\n".join(lines),
    "class":   css,
}))
