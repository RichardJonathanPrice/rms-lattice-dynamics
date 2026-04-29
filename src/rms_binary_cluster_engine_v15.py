import os
import json
import csv
from datetime import datetime
from collections import deque

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter


def run_rms(preset_name: str, config: dict, project_root: str, runs_root: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RUN_ID = f"{preset_name}_{timestamp}"
    RUN_DIR = os.path.join(runs_root, RUN_ID)
    os.makedirs(RUN_DIR, exist_ok=True)

    # -----------------------------
    # PARAMETERS
    # -----------------------------
    N = config["N"]
    steps = config["steps"]
    seed_density = config["seed_density"]
    self_weight = config["self_weight"]
    nbr_weight = config["nbr_weight"]
    threshold = config["threshold"]
    noise = config["noise"]
    seed = config["seed"]

    capture_every = config.get("capture_every", 5)
    gif_fps = config.get("gif_fps", 25)
    rolling_window = 50

    rng = np.random.default_rng(seed)
    state = (rng.random((N, N)) < seed_density).astype(np.float32)

    def neighbour_mean(x):
        s = (
            np.roll(x, 1, 0) + np.roll(x, -1, 0) +
            np.roll(x, 1, 1) + np.roll(x, -1, 1) +
            np.roll(np.roll(x, 1, 0), 1, 1) +
            np.roll(np.roll(x, 1, 0), -1, 1) +
            np.roll(np.roll(x, -1, 0), 1, 1) +
            np.roll(np.roll(x, -1, 0), -1, 1)
        )
        return s / 8.0

    def cluster_metrics(binary_state):
        visited = np.zeros(binary_state.shape, dtype=bool)
        sizes = []

        rows, cols = binary_state.shape

        for i in range(rows):
            for j in range(cols):
                if binary_state[i, j] != 1 or visited[i, j]:
                    continue

                stack = [(i, j)]
                visited[i, j] = True
                size = 0

                while stack:
                    x, y = stack.pop()
                    size += 1

                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            nx = (x + dx) % rows
                            ny = (y + dy) % cols

                            if binary_state[nx, ny] == 1 and not visited[nx, ny]:
                                visited[nx, ny] = True
                                stack.append((nx, ny))

                sizes.append(size)

        if not sizes:
            return 0, 0, 0

        sizes = np.array(sizes)
        multi = sizes[sizes >= 2]

        return len(multi), int(np.max(sizes)), float(np.sum(multi) / binary_state.size)

    # -----------------------------
    # TELEMETRY
    # -----------------------------
    telemetry_path = os.path.join(RUN_DIR, "telemetry.csv")

    with open(telemetry_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "step",
            "active_fraction",
            "changed_fraction",
            "multi_cell_cluster_count",
            "largest_cluster_size",
            "multicell_active_fraction",
            "multi_cell_cluster_count_rolling",
            "largest_cluster_size_rolling",
        ])

    cluster_window = deque(maxlen=rolling_window)
    largest_window = deque(maxlen=rolling_window)

    # -----------------------------
    # GIF SETUP
    # -----------------------------
    fig, ax = plt.subplots()
    im = ax.imshow(state, animated=True)
    ax.axis("off")

    gif_path = os.path.join(RUN_DIR, "run.gif")
    writer = PillowWriter(fps=gif_fps)

    with writer.saving(fig, gif_path, dpi=100):
        writer.grab_frame()

        for t in range(1, steps + 1):
            prev = state.copy()

            nbr = neighbour_mean(state)
            pressure = self_weight * state + nbr_weight * nbr
            next_state = (pressure >= threshold).astype(np.float32)

            flips = rng.random((N, N)) < noise
            next_state[flips] = 1.0 - next_state[flips]

            state = next_state

            active = float(np.mean(state))
            changed = float(np.mean(state != prev))

            cluster_count, largest, multi_frac = cluster_metrics(state)

            cluster_window.append(cluster_count)
            largest_window.append(largest)

            with open(telemetry_path, "a", newline="") as f:
                writer_csv = csv.writer(f)
                writer_csv.writerow([
                    t,
                    active,
                    changed,
                    cluster_count,
                    largest,
                    multi_frac,
                    float(np.mean(cluster_window)),
                    float(np.mean(largest_window)),
                ])

            if t % capture_every == 0:
                im.set_data(state)
                writer.grab_frame()

    plt.close(fig)

    return {
        "run_id": RUN_ID,
        "preset": preset_name,
        "final_active": active,
        "final_clusters": cluster_count,
        "largest_cluster": largest,
        "multi_frac": multi_frac,
    }