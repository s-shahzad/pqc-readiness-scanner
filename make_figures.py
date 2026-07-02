#!/usr/bin/env python3
"""Generate black-and-white figures for the paper from the real scan JSON.

No fabricated numbers: every value is read from the committed scan results and
the section headers in the host list files.
"""
import json, re, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = pathlib.Path(__file__).resolve().parent
OUT = R / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": "black", "axes.linewidth": 0.8,
    "figure.dpi": 200, "savefig.bbox": "tight",
})

VERTICAL_MAP = [
    ("EV charging", "ev"), ("MQTT", "mqtt"), ("OT / ICS", "auto"),
    ("Industrial automation", "auto"), ("Energy", "energy"),
    ("Building automation", "hvac"), ("Water", "energy"),
]

def vertical_of_section(text):
    for needle, key in VERTICAL_MAP:
        if needle.lower() in text.lower():
            return key
    return "other"

def host_to_vertical():
    mapping = {}
    for f in ["ot-iot-hosts.txt", "ot-iot-hosts-2.txt", "ot-iot-hosts-3.txt"]:
        cur = "other"
        for line in (R / f).read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("#"):
                m = re.match(r"#\s*-*\s*(.+?)\s*-*$", s)
                if m and "---" in line:
                    cur = vertical_of_section(m.group(1))
                continue
            if not s:
                continue
            host = s.split(":")[0]
            mapping[host] = cur
    return mapping

def verdict_class(v):
    if v.startswith("MIGRATED"): return "migrated"
    if v.startswith("PARTIAL"): return "migrated"   # PQC-capable counts as migrated-capable
    if v.startswith("CLASSICAL"): return "classical"
    return "unknown"

def load(*files):
    rows = {}
    for f in files:
        for r in json.load(open(R / f)):
            rows[r["host"]] = verdict_class(r["verdict"])
    return rows

# ---- Figure 1: classical-only % by vertical (real counts) ----
vmap = host_to_vertical()
res = load("seed-ot-iot.json", "seed-ot-iot-2.json", "seed-ot-iot-3.json")
web = load("scan-results.json")

LABELS = {"auto": "Industrial\nautomation", "mqtt": "MQTT\nbrokers",
          "energy": "Energy /\ngrid", "ev": "EV charging",
          "hvac": "Building\nHVAC"}
counts = {}
for host, cls in res.items():
    key = vmap.get(host, "other")
    if key not in LABELS:
        continue
    d = counts.setdefault(key, {"classical": 0, "migrated": 0, "unknown": 0})
    d[cls] += 1

# web baseline bar
wc = {"classical": 0, "migrated": 0, "unknown": 0}
for cls in web.values():
    wc[cls] += 1

rows = []
for key, lab in LABELS.items():
    d = counts.get(key)
    if not d:
        continue
    resolvable = d["classical"] + d["migrated"]
    if resolvable == 0:
        continue
    pct = 100.0 * d["classical"] / resolvable
    rows.append((lab, pct, resolvable))
rows.sort(key=lambda x: -x[1])
web_res = wc["classical"] + wc["migrated"]
web_pct = 100.0 * wc["classical"] / web_res

fig, ax = plt.subplots(figsize=(5.4, 3.0))
labels = [r[0] for r in rows] + ["Web\nbaseline"]
vals = [r[1] for r in rows] + [web_pct]
ns = [r[2] for r in rows] + [web_res]
hatches = ["////"] * len(rows) + [".."]
bars = ax.bar(range(len(vals)), vals, color="white", edgecolor="black", hatch=None)
for b, h in zip(bars, hatches):
    b.set_hatch(h)
ax.axhline(web_pct, color="black", ls="--", lw=0.7)
ax.set_xticks(range(len(vals)))
ax.set_xticklabels(labels)
ax.set_ylabel("Classical-only by default (%)")
ax.set_ylim(0, 100)
for i, (v, n) in enumerate(zip(vals, ns)):
    ax.text(i, v + 2, f"{v:.0f}%\n(n={n})", ha="center", va="bottom", fontsize=7)
ax.set_title("PQC readiness by vertical (2026-06-25, N=124 OT/IoT + 40 web)", fontsize=9)
fig.savefig(OUT / "verticals.pdf")
plt.close(fig)

# ---- Figure 2: longitudinal verdict stability (real T0 vs T1) ----
base = load("seed-ot-iot.json", "seed-ot-iot-2.json", "seed-ot-iot-3.json")
new = load("rescan-ot-iot-2026-07-02.json")
webb = load("scan-results.json")
webn = load("rescan-web-2026-07-02.json")

def stability(b, n):
    same = sum(1 for k in n if k in b and b[k] == n[k])
    tot = sum(1 for k in n if k in b)
    return same, tot

ot_same, ot_tot = stability(base, new)
w_same, w_tot = stability(webb, webn)

fig, ax = plt.subplots(figsize=(4.6, 2.8))
cats = ["OT/IoT\n(N=124)", "Web\n(N=40)"]
same = [ot_same, w_same]
changed = [ot_tot - ot_same, w_tot - w_same]
x = range(len(cats))
b1 = ax.bar(x, same, color="white", edgecolor="black", hatch="////", label="unchanged")
b2 = ax.bar(x, changed, bottom=same, color="black", edgecolor="black", label="changed")
ax.set_xticks(list(x))
ax.set_xticklabels(cats)
ax.set_ylabel("Hosts")
ax.set_title("Verdict stability, 2026-06-25 to 2026-07-02 (7 days)", fontsize=9)
for i, (s, t) in enumerate(zip(same, [ot_tot, w_tot])):
    ax.text(i, t + 1.5, f"{s}/{t}\nstable", ha="center", va="bottom", fontsize=7)
ax.legend(frameon=False, fontsize=7, loc="lower right")
ax.set_ylim(0, max(ot_tot, w_tot) + 18)
fig.savefig(OUT / "longitudinal.pdf")
plt.close(fig)

print("wrote:", OUT / "verticals.pdf", "and", OUT / "longitudinal.pdf")
print(f"OT stability {ot_same}/{ot_tot}, web stability {w_same}/{w_tot}")
print("vertical rows:", rows, "web_pct", round(web_pct,1))
