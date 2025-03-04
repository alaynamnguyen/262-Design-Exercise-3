import pandas as pd
import numpy as np
import os
import re

# Define paths
log_dir = "log/"

# Regular expression patterns to extract log entries and clock rate
log_pattern = re.compile(r"(.+?) \| ([\d.]+) \| (\d+) \| (\d+)")
clock_rate_pattern = re.compile(r"Clock Rate: (\d+) ticks per second")

# Function to read log file and extract data
def read_log(file_path):
    """Extracts system time, logical clock values, queue length, and clock rate from a log file."""
    system_time = []
    logical_clock = []
    queue_length = []
    clock_rate = None

    with open(file_path, "r") as file:
        for line in file:
            if clock_rate is None:  # Extract clock rate from the first line
                match_clock = clock_rate_pattern.match(line.strip())
                if match_clock:
                    clock_rate = int(match_clock.group(1))

            match = log_pattern.match(line.strip())
            if match:
                event_type, sys_time, queue_len, log_clock = match.groups()
                system_time.append(float(sys_time))
                queue_length.append(int(queue_len))
                logical_clock.append(int(log_clock))

    return system_time, logical_clock, queue_length, clock_rate

# Function to compute statistics from logs
def compute_log_statistics(log_file):
    """Computes average jump size in logical clock and average queue length."""
    system_time, logical_clock, queue_length, clock_rate = read_log(log_file)

    avg_jump_size = np.mean(np.abs(np.diff(logical_clock))) if len(logical_clock) > 1 else 0
    avg_queue_length = np.mean(queue_length) if queue_length else 0

    return clock_rate, avg_jump_size, avg_queue_length

# Discover all log files
log_files = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")])

# Create a dictionary to store the results
summary_data = {}

# Process all log files and group them by run ID (e.g., A1, B1, C1 → Run 1, A1_custom, B1_custom, C1_custom → Run 1_custom)
for log_file in log_files:
    log_path = os.path.join(log_dir, log_file)

    # Extract process (A, B, or C) and run ID, including variations like `custom`, `166`
    match = re.match(r"([A-C])(\d+)(_.*)?\.log", log_file)
    if not match:
        continue  # Skip files that don't match expected pattern

    process, run_id, variant = match.groups()
    run_id = f"Run {run_id}{variant if variant else ''}"  # Standardize run ID format with custom tags

    if run_id not in summary_data:
        summary_data[run_id] = {"Log File": run_id}

    clock_speed, avg_jump, avg_queue = compute_log_statistics(log_path)

    # Store statistics for the corresponding process
    summary_data[run_id][f"{process} Clock Speed"] = clock_speed
    summary_data[run_id][f"{process} Avg Jump"] = avg_jump
    summary_data[run_id][f"{process} Avg Queue Len"] = avg_queue

# Convert dictionary to DataFrame and ensure columns are sorted correctly
columns = [
    "Log File", "A Clock Speed", "B Clock Speed", "C Clock Speed",
    "A Avg Jump", "B Avg Jump", "C Avg Jump",
    "A Avg Queue Len", "B Avg Queue Len", "C Avg Queue Len"
]
df_summary = pd.DataFrame(summary_data.values(), columns=columns)

# Save the table to CSV
csv_filename = "plots/log_summary.csv"
df_summary.to_csv(csv_filename, index=False)
print(f"Summary saved: {csv_filename}")

# Print the table for easy reference
print(df_summary)
