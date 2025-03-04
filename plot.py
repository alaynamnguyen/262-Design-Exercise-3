import matplotlib.pyplot as plt
import argparse
import numpy as np
import os
import re

parser = argparse.ArgumentParser(description="Run a virtual machine process.")
parser.add_argument("--mode", default="default", type=str, choices=["default", "small", "custom"])
args = parser.parse_args()
mode = args.mode

# Define process names and run IDs
processes = ["A", "B", "C"]
runs = range(1, 6)

# Regular expression patterns to extract log entries and clock rate
log_pattern = re.compile(r"(.+?) \| ([\d.]+) \| (\d+) \| (\d+)")
clock_rate_pattern = re.compile(r"Clock Rate: (\d+) ticks per second")

# Function to read log file and extract data
def read_log(file_path):
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

# Function to plot all three graphs into one figure
def plot_combined_graphs(system_times_logical, system_times_queue, clock_rates, filename):
    fig, axes = plt.subplots(3, 1, figsize=(10, 15), sharex=True)

    # Define colors for A, B, C
    colors = {"A": "blue", "B": "red", "C": "green"}

    # Plot Logical Clock Over Time
    for process, sys_time, y_values in system_times_logical:
        clock_rate = clock_rates[process]  # Get clock rate
        label = f"{process} (Clock Rate: {clock_rate})"
        axes[0].plot(sys_time, y_values, marker='.', markersize=1, linestyle='-', color=colors[process], label=label)
    axes[0].set_ylabel("Logical Clock")
    axes[0].set_title("Logical Clock Over Time")
    axes[0].legend()
    axes[0].grid(True)

    # Compute Logical Clock Drift
    all_times = sorted(set(time for _, sys_time, _ in system_times_logical for time in sys_time))
    interpolated_clocks = {}
    for process, sys_time, y_values in system_times_logical:
        interp_func = np.interp(all_times, sys_time, y_values)  # Interpolation
        interpolated_clocks[process] = interp_func

    min_logical_clock = np.min(np.array(list(interpolated_clocks.values())), axis=0)
    
    for process, y_values in interpolated_clocks.items():
        clock_rate = clock_rates[process]
        label = f"{process} (Clock Rate: {clock_rate})"
        drift = y_values - min_logical_clock  # Compute drift
        axes[1].plot(all_times, drift, marker='.', markersize=1, linestyle='-', color=colors[process], label=label)
    axes[1].set_ylabel("Logical Clock Drift")
    axes[1].set_title("Logical Clock Drift Over Time")
    axes[1].legend()
    axes[1].grid(True)

    # Plot Queue Length Over Time
    for process, sys_time, y_values in system_times_queue:
        clock_rate = clock_rates[process]  # Get clock rate
        label = f"{process} (Clock Rate: {clock_rate})"
        axes[2].plot(sys_time, y_values, marker='.', markersize=1, linestyle='-', color=colors[process], label=label)
    axes[2].set_xlabel("System Time")
    axes[2].set_ylabel("Queue Length")
    axes[2].set_title("Queue Length Over Time")
    axes[2].legend()
    axes[2].grid(True)

    # Save the combined figure
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# Process each run
for run_id in runs:
    system_times_logical = []
    system_times_queue = []
    clock_rates = {}

    for process in processes:
        log_file = f"log/{process}{run_id}{'_' + mode if mode != 'default' else ''}.log"

        if os.path.exists(log_file):
            system_time, logical_clock, queue_length, clock_rate = read_log(log_file)

            # Store system times and values for plotting
            system_times_logical.append((process, system_time, logical_clock))
            system_times_queue.append((process, system_time, queue_length))
            clock_rates[process] = clock_rate  # Store clock rate

            print(f"Processed {log_file} with Clock Rate: {clock_rate}")
        else:
            print(f"Log file {log_file} not found, skipping.")

    # Generate one PDF file per run, stacking all three graphs
    if system_times_logical and system_times_queue:
        output_file = f"plots/combined_plot_{run_id}{'_' + mode if mode != 'default' else ''}.pdf"
        plot_combined_graphs(system_times_logical, system_times_queue, clock_rates, output_file)
        print(f"Saved combined plot: {output_file}")
