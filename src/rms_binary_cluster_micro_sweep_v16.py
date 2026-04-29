import os
import csv
import yaml
from datetime import datetime
from itertools import product

from rms_binary_cluster_engine_v15 import run_rms


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "rms_binary_cluster_micro_sweep_v16.yaml")
RUNS_ROOT = os.path.join(PROJECT_ROOT, "runs")

os.makedirs(RUNS_ROOT, exist_ok=True)


def safe_float_label(value):
    return str(value).replace(".", "p")


with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
sweep_id = f"{cfg['sweep_name']}_{timestamp}"
sweep_root = os.path.join(RUNS_ROOT, sweep_id)

os.makedirs(sweep_root, exist_ok=True)

base = cfg["base"]
sweep = cfg["sweep"]

summary_path = os.path.join(sweep_root, "micro_sweep_summary.csv")

summary_columns = [
    "run_index",
    "preset_name",
    "threshold",
    "self_weight",
    "nbr_weight",
    "noise",
    "seed_density",
    "seed",
    "final_active",
    "final_clusters",
    "largest_cluster",
    "multi_frac",
    "run_id",
]

results = []

total_runs = (
    len(sweep["threshold"])
    * len(sweep["self_weight"])
    * len(sweep["noise"])
    * len(sweep["seed_density"])
    * len(sweep["seed"])
)

print(f"Starting micro sweep: {sweep_id}")
print(f"Total runs: {total_runs}")
print(f"Output folder: {sweep_root}")

run_index = 0

for threshold, self_weight, noise, seed_density, seed in product(
    sweep["threshold"],
    sweep["self_weight"],
    sweep["noise"],
    sweep["seed_density"],
    sweep["seed"],
):
    run_index += 1
    nbr_weight = round(1.0 - float(self_weight), 10)

    preset_name = (
        f"v16_run_{run_index:04d}"
        f"_thr_{safe_float_label(threshold)}"
        f"_self_{safe_float_label(self_weight)}"
        f"_noise_{safe_float_label(noise)}"
        f"_dens_{safe_float_label(seed_density)}"
        f"_seed_{seed}"
    )

    preset = dict(base)
    preset.update({
        "threshold": float(threshold),
        "self_weight": float(self_weight),
        "nbr_weight": nbr_weight,
        "noise": float(noise),
        "seed_density": float(seed_density),
        "seed": int(seed),
    })

    print(f"[{run_index}/{total_runs}] Running {preset_name}")

    result = run_rms(
        preset_name=preset_name,
        config=preset,
        project_root=PROJECT_ROOT,
        runs_root=sweep_root,
    )

    row = {
        "run_index": run_index,
        "preset_name": preset_name,
        "threshold": threshold,
        "self_weight": self_weight,
        "nbr_weight": nbr_weight,
        "noise": noise,
        "seed_density": seed_density,
        "seed": seed,
        "final_active": result["final_active"],
        "final_clusters": result["final_clusters"],
        "largest_cluster": result["largest_cluster"],
        "multi_frac": result["multi_frac"],
        "run_id": result["run_id"],
    }

    results.append(row)

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_columns)
        writer.writeheader()
        writer.writerows(results)

print("Micro sweep complete.")
print(f"Summary written to: {summary_path}")