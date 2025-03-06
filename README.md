# CS 2620 Design Exercise 3

This project simulates a logical clock system in a distributed environment with three processes (A, B, C) that communicate asynchronously. The system models message-passing between processes, updates logical clocks based on received messages, and logs events for analysis.

## To generate proto

```sh
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. logical_clock.proto
```

## To run unit tests

```sh
pytest -p no:warnings test_logical_clock.py
```

## To run system

```sh
python run.py {process id} {run id} --mode {mode}
```

-   Process id: "A", "B", "C".
-   Run id: Any string to specify the run.
-   Mode: "default", "small", "custom", "166".
    -   "default": Process A, B, and C runs at random clock rate between 1 and 6 and 0.3 probability of external events
    -   "small": processes are run with a higher probability of external events and smaller variance in their clock speeds
    -   "custom": processes are run with clock speeds 1, 3, and 6
    -   "166": runs process A at clock rate 1 and the other two processes at clock rate 6

## To plot the logical clock, drift, and queue lengths for each log file

```sh
python plot.py --mode {mode}
```

-   Mode: "default", "small", "custom", "166"

## To generate table with avg jumps and avg queue lengths

```sh
python table.py
```

## Bonus experiments beyond the assigned ones

We experimented with different probability distributions for events, not just the case where there is a smaller probability of an event being internal. Example: In Custom Run 3, we used a high probability of an event being internal, which provided additional insights into the interaction between process speed and internal vs. external event rates. For this case, we saw low queue lengths which made sense since less events were external so processes would have received less messages.
