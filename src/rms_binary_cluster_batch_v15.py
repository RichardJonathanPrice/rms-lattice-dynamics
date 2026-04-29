import os
import csv
import yaml

from rms_binary_cluster_engine_v15 import run_rms


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "rms_binary_cluster_presets_v15.yaml")
RUNS_ROOT = os.path.join(PROJECT_ROOT, "runs")

os.makedirs(RUNS_ROOT, exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

summary_path = os.path.join(RUNS_ROOT, "batch_summary.csv")

results = []

for name, preset in cfg["presets"].items():
    print(f"Running preset: {name}")
    result = run_rms(
        preset_name=name,
        config=preset,
        project_root=PROJECT_ROOT,
        runs_root=RUNS_ROOT,
    )
    results.append(result)

with open(summary_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print("Batch complete.")
print(f"Summary written to: {summary_path}")