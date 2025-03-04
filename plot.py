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
# runs = range(1, 6)  # i in 1...5
runs = range(1, 2)

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

# Function to plot all processes on the same graph
def plot_combined(system_times, y_label, title, filename, clock_rates):
    plt.figure(figsize=(10, 10))
    
    # Define colors for A, B, C
    colors = {"A": "blue", "B": "red", "C": "green"}
    for process, sys_time, y_values in system_times:
        clock_rate = clock_rates[process]  # Get clock rate
        label = f"{process} (Clock Rate: {clock_rate})"
        plt.plot(sys_time, y_values, marker='.', markersize=1, linestyle='-', color=colors[process], label=label)

    plt.xlabel("System Time")
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()  # Show legend with clock rates
    plt.grid(True)
    plt.savefig(filename)
    plt.close()

# Function to plot logical clock drift over time
def plot_logical_clock_drift(system_times, title, filename, clock_rates):
    plt.figure(figsize=(8, 5))

    # Define colors for A, B, C
    colors = {"A": "blue", "B": "red", "C": "green"}

    # Collect all unique system times from all processes
    all_times = sorted(set(time for _, sys_time, _ in system_times for time in sys_time))

    # Interpolate logical clocks so all processes have the same timestamps
    interpolated_clocks = {}
    for process, sys_time, y_values in system_times:
        interp_func = np.interp(all_times, sys_time, y_values)  # Interpolation
        interpolated_clocks[process] = interp_func

    # Compute drift relative to the minimum logical clock at each timestamp
    min_logical_clock = np.min(np.array(list(interpolated_clocks.values())), axis=0)

    for process, y_values in interpolated_clocks.items():
        clock_rate = clock_rates[process]
        label = f"{process} (Clock Rate: {clock_rate})"
        
        drift = y_values - min_logical_clock  # Compute drift
        plt.plot(all_times, drift, marker='o', markersize=1, linestyle='-', color=colors[process], label=label)

    plt.xlabel("System Time")
    plt.ylabel("Logical Clock Drift")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(filename)
    plt.close()

# Process each run
for run_id in runs:
    system_times_logical = []
    system_times_queue = []
    clock_rates = {}

    for process in processes:
        # log_file = f"log/{process}{run_id}.log"
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

    # Plot all processes on the same graph
    if system_times_logical:
        plot_combined(system_times_logical, "Logical Clock",
                      "Logical Clock over Time", f"plots/logical_clock{run_id}{'_' + mode if mode != 'default' else ''}.pdf", clock_rates)

        plot_logical_clock_drift(system_times_logical, "Logical Clock Drift over Time",
                                 f"plots/logical_clock_drift{run_id}{'_' + mode if mode != 'default' else ''}.pdf", clock_rates)

    if system_times_queue:
        plot_combined(system_times_queue, "Queue Length",
                      "Queue Length over Time", f"plots/queue_len{run_id}{'_' + mode if mode != 'default' else ''}.pdf", clock_rates)

    print(f"Plots generated for run {run_id}")
