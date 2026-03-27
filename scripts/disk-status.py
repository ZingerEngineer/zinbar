#!/usr/bin/env python3
import json, subprocess, os

EXCLUDE_FSTYPES = {
    'tmpfs', 'devtmpfs', 'squashfs', 'overlay', 'efivarfs',
    'bpf', 'cgroup2', 'proc', 'sysfs', 'securityfs', 'pstore',
    'debugfs', 'tracefs', 'configfs', 'fusectl', 'hugetlbfs',
    'mqueue', 'ramfs', 'autofs', 'nsfs',
}

result = subprocess.run(
    ['df', '-h', '--output=target,fstype,source,size,used,avail,pcent'],
    capture_output=True, text=True
)

entries = []
for line in result.stdout.strip().split('\n')[1:]:
    parts = line.split()
    if len(parts) < 7:
        continue
    target, fstype, source = parts[0], parts[1], parts[2]
    size, used, avail, pcent = parts[3], parts[4], parts[5], parts[6]

    if fstype in EXCLUDE_FSTYPES:
        continue
    if 'loop' in source:
        continue
    if any(target.startswith(p) for p in ['/run/', '/sys/', '/proc/', '/dev/']):
        continue

    pct_int = int(pcent.rstrip('%'))
    dev_name = os.path.basename(source)
    entries.append((target, dev_name, size, used, avail, pcent, pct_int))

# Build tooltip lines
lines = []
for target, dev, size, used, avail, pcent, _ in entries:
    lines.append(f"󰋊 {target}  [{dev}]")
    lines.append(f"  Used:   {used}  ({pcent})")
    lines.append(f"  Free:   {avail}")
    lines.append(f"  Total:  {size}")
    lines.append("")
tooltip = '\n'.join(lines).rstrip('\n')

# Root pct for the button text; worst pct for alert class
root_pct = next((e[6] for e in entries if e[0] == '/'), 0)
worst_pct = max((e[6] for e in entries), default=0)

css_class = 'critical' if worst_pct > 85 else ('warning' if worst_pct > 70 else '')

print(json.dumps({
    'text':    f'󰋊  {root_pct}%',
    'tooltip': tooltip,
    'class':   css_class,
}))
