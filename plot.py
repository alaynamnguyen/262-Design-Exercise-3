import matplotlib.pyplot as plt
import os
import re

# Define process names and run IDs
processes = ["A", "B", "C"]
runs = range(1, 6)  # i in 1...5

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
    plt.figure(figsize=(8, 10))
    
    # Define colors for A, B, C
    colors = {"A": "blue", "B": "red", "C": "green"}
    for process, sys_time, y_values in system_times:
        clock_rate = clock_rates[process]  # Get clock rate
        label = f"{process} (Clock Rate: {clock_rate})"
        plt.plot(sys_time, y_values, marker='o', linestyle='-', color=colors[process], label=label)

    plt.xlabel("System Time")
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()  # Show legend with clock rates
    plt.grid(True)
    plt.savefig(filename)
    plt.close()

# Process each run
for run_id in runs:
    system_times_logical = []
    system_times_queue = []
    clock_rates = {}

    for process in processes:
        log_file = f"log/{process}{run_id}.log"

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
                      "Logical Clock over Time", f"plots/logical_clock{run_id}.png", clock_rates)

    if system_times_queue:
        plot_combined(system_times_queue, "Queue Length",
                      "Queue Length over Time", f"plots/queue_len{run_id}.png", clock_rates)

    print(f"Plots generated for run {run_id}")
