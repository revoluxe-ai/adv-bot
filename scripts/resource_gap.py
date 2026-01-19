import json
from pathlib import Path

def parse_cpu(value):
    if value is None:
        return None
    if value.endswith('m'):
        return float(value[:-1])
    if value.endswith('n'):
        return float(value[:-1]) / 1_000_000
    return float(value) * 1000

path = Path('./pods.json')
if not path.exists():
    raise SystemExit('pods.json missing')

pods = json.loads(path.read_text(encoding='utf-16'))
diffs = []
for item in pods.get('items', []):
    ns = item['metadata']['namespace']
    pod = item['metadata']['name']
    for container in item['spec'].get('containers', []):
        name = container['name']
        resources = container.get('resources', {})
        req = resources.get('requests', {}).get('cpu')
        lim = resources.get('limits', {}).get('cpu')
        req_val = parse_cpu(req) if req else None
        lim_val = parse_cpu(lim) if lim else None
        if req_val is None or lim_val is None:
            continue
        diff = lim_val - req_val
        if diff <= 0:
            continue
        diffs.append((diff, ns, pod, name, req, lim))

diffs.sort(reverse=True)
for diff, ns, pod, name, req, lim in diffs[:10]:
    print(f"{ns}/{pod}/{name}: request={req} limit={lim} diff_mCPU={diff:.1f}")
