import csv
from collections import defaultdict
import matplotlib.pyplot as plt

INPUT_FILE = "node_power_levels_over_time.csv"
OUTPUT_FILE = "avg_power_by_time.csv"

# --- Step 1: Read CSV and aggregate power by time ---
power_by_time = defaultdict(list)

with open(INPUT_FILE, "r", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        t   = int(row["time"])
        pwr = float(row["power"])

        # filter out invalid > 90000
        if pwr <= 90000:
            power_by_time[t].append(pwr)

# --- Step 2: Compute average power per timestep ---
times = sorted(power_by_time.keys())
avg_power = []

for t in times:
    values = power_by_time[t]
    if values:
        avg_power.append(sum(values) / len(values))
    else:
        avg_power.append(0)

# --- Step 3: Write averaged results to CSV ---
with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["time", "avg_power"])
    writer.writeheader()
    for t, avg in zip(times, avg_power):
        writer.writerow({"time": t, "avg_power": avg})

print(f"Done. Output saved to {OUTPUT_FILE}")

# --- Step 4: Plot the results ---
plt.figure(figsize=(10,5))
plt.plot(times, avg_power, marker='o')
plt.title("Average Node Power Over Time")
plt.xlabel("Simulation Time")
plt.ylabel("Average Power (Joules)")
plt.grid(True)
plt.tight_layout()
plt.show()