import grpc
from concurrent import futures
import time
import threading
import queue
import random
import logical_clock_pb2
import logical_clock_pb2_grpc
import argparse

config = {
    "default": {
        "A": {
            "clock_rate": random.randint(1, 6),
            "max_action": 10,
        },
        "B": {
            "clock_rate": random.randint(1, 6),
            "max_action": 10,
        },
        "C": {
            "clock_rate": random.randint(1, 6),
            "max_action": 10,
        }
    },
    "small": {
        "A": {
            "clock_rate": random.randint(2, 3),
            "max_action": 4,
        },
        "B": {
            "clock_rate": random.randint(2, 3),
            "max_action": 4,
        },
        "C": {
            "clock_rate": random.randint(2, 3),
            "max_action": 4,
        },
    },
    "custom": {
        "A": {
            "clock_rate": 3,
            "max_action": 20,
        },
        "B": {
            "clock_rate": 2,
            "max_action": 20,
        },
        "C": {
            "clock_rate": 2,
            "max_action": 20,
        }
    }, 
    "166": {
        "A": {
            "clock_rate": 1,
            "max_action": 10,
        },
        "B": {
            "clock_rate": 6,
            "max_action": 10,
        },
        "C": {
            "clock_rate": 6,
            "max_action": 10,
        }
    }
}

class ClockService(logical_clock_pb2_grpc.ClockServiceServicer):
    """Handles incoming messages and updates logical clock."""

    def __init__(self, process):
        self.process = process  # Reference to the main process object
    
    def ReadyCheck(self, request, context):
        """Returns whether this process is ready to start."""
        return logical_clock_pb2.ReadyResponse(is_ready=self.is_ready)

    def FinishCheck(self, request, context):
        """Returns whether this process has finished execution."""
        print(f"FinishCheck called by {request.sender_id} -> returning {self.process.is_finished}")
        return logical_clock_pb2.FinishResponse(is_finished=self.process.is_finished)

    def SendMessage(self, request, context):
        """Handles received messages and places them in the event queue."""
        system_time = time.time()
        self.process.event_queue.put((request.sender_id, request.logical_clock, system_time))
        return logical_clock_pb2.Ack(message=f"Ack from {self.process.process_id}")

class VirtualMachine:
    """Represents a logical machine with a clock and gRPC server/client."""

    def __init__(self, process_id, port, num_to_port, run_id, port_mapping, mode):
        self.process_id = process_id
        self.port = port
        self.num_to_port = num_to_port
        self.logical_clock = 0
        self.clock_rate = config[mode][self.process_id]["clock_rate"]
        self.event_queue = queue.Queue()
        self.mode = mode
        self.log_file = f"log/{process_id}{run_id}{'_' + self.mode if self.mode != 'default' else ''}.log"
        self.is_finished = False
        self.port_to_process = {v: k for k, v in port_mapping.items()}
        
        # Create ClockService instance and share it with gRPC
        self.service = ClockService(self)

        # Start the gRPC server in a separate thread
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()

        time.sleep(2)  # Allow server to start before processing

        # Wait until all processes are ready
        self.wait_for_all_servers_ready()

    def start_server(self):
        """Initializes and starts the gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=3))
        service = ClockService(self)
        logical_clock_pb2_grpc.add_ClockServiceServicer_to_server(service, server)
        server.add_insecure_port(f"[::]:{self.port}")
        server.start()

        # Mark the service as ready
        service.is_ready = True

        print(f"{self.process_id} Server started on port {self.port}...")
        server.wait_for_termination()

    def wait_for_all_servers_ready(self):
        """Waits until all other processes report they are ready."""
        print(f"{self.process_id} waiting for all servers to be ready...")

        all_ready = False
        while not all_ready:
            time.sleep(1)  # Avoid spamming requests
            all_ready = True
            for target_port in self.num_to_port.values():
                try:
                    channel = grpc.insecure_channel(f"localhost:{target_port}")
                    stub = logical_clock_pb2_grpc.ClockServiceStub(channel)
                    response = stub.ReadyCheck(logical_clock_pb2.ReadyRequest())
                    if not response.is_ready:
                        all_ready = False
                        break  # If any machine isn't ready, break and retry
                except grpc.RpcError:
                    all_ready = False  # Assume not ready if unreachable

        print(f"{self.process_id} detected all servers are ready. Proceeding...")

    def wait_for_all_to_finish(self):
        """Waits until all processes finish before terminating."""
        print(f"{self.process_id} waiting for all processes to finish...")

        while True:
            time.sleep(1)  # Avoid spamming requests
            all_finished = True  # Assume all are finished unless proven otherwise

            for target_port in self.num_to_port.values():
                print(f"Checking if {target_port} finished")
                try:
                    channel = grpc.insecure_channel(f"localhost:{target_port}")
                    stub = logical_clock_pb2_grpc.ClockServiceStub(channel)
                    response = stub.FinishCheck(logical_clock_pb2.FinishRequest(sender_id=self.process_id))
                    print(f"    {target_port} finished: {response.is_finished}")
                    if not response.is_finished:
                        all_finished = False  # At least one process is still running
                        break
                except grpc.RpcError:
                    print(f"    {target_port} finished: RpcError")
                    pass # Assume not finished if unreachable

            if all_finished:
                break  # Exit loop once all processes report they are finished

        print(f"{self.process_id} detected all processes have finished. Shutting down...")

    def log_event(self, event_type, system_time, queue_length):
        """Logs all events in a single file per process."""
        with open(self.log_file, "a") as log:
            log.write(f"{event_type} | {system_time} | {queue_length} | {self.logical_clock}\n")

    def process_message(self, sender_id, received_clock, system_time):
        """Processes a received message and updates logical clock."""
        print("Old local clock:", self.logical_clock, "Received clock:", received_clock, "New logical clock:", max(self.logical_clock, received_clock) + 1)
        self.logical_clock = max(self.logical_clock, received_clock) + 1
        queue_length = self.event_queue.qsize()
        self.log_event(f"RECEIVE {sender_id}", system_time, queue_length)

    def send_message(self, target_port):
        """Sends a logical clock message to another process."""
        channel = grpc.insecure_channel(f"localhost:{target_port}")
        stub = logical_clock_pb2_grpc.ClockServiceStub(channel)
        message = logical_clock_pb2.ClockMessage(
            sender_id=self.process_id,
            logical_clock=self.logical_clock,
            system_time=time.time()
        )
        response = stub.SendMessage(message)
        print(f"{self.process_id} -> Sent message to {target_port} | LC: {self.logical_clock} | Response: {response.message}")

    def run(self):
        """Main event loop: process messages or generate events based on clock rate."""
        with open(self.log_file, "w") as log:
            log.write(f"Clock Rate: {self.clock_rate} ticks per second\n")
            log.write(f"{'-' * 40}\n")  # Add a separator for clarity

        start_time = time.time()
        duration = 65  # Run for 1 minute and 5 seconds
        while time.time() - start_time < duration:
            st = time.time()
            if not self.event_queue.empty():
                sender_id, received_clock, system_time = self.event_queue.get()
                # self.process_message(sender_id, received_clock, system_time)  # bug
                self.process_message(sender_id, received_clock, time.time())
            else:
                action = random.randint(1, config[mode][self.process_id]['max_action'])
                if action < 3:  # Send to one machine (action is 1 or 2)
                    target = num_to_port[action]
                    target_process = self.port_to_process[target]
                    self.logical_clock += 1
                    self.send_message(target)
                    self.log_event(f"SEND {target_process}", time.time(), self.event_queue.qsize())

                elif action == 3:  # Send to both machines
                    self.logical_clock += 1
                    for target in self.num_to_port.values():
                        self.send_message(target)
                    self.log_event("SEND ALL", time.time(), self.event_queue.qsize())

                else:  # Internal event
                    self.logical_clock += 1
                    self.log_event("INTERNAL", time.time(), self.event_queue.qsize())
            time.sleep((1 / self.clock_rate) - (time.time() - st))
        
        # Mark this process as finished
        self.is_finished = True
        print(f"{self.process_id} has finished execution.")

        # Wait for all other processes to finish
        self.wait_for_all_to_finish()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a virtual machine process.")
    parser.add_argument("process_id", choices=["A", "B", "C"], help="Process ID (A, B, or C)")
    parser.add_argument("run_id", type=int)
    parser.add_argument("--mode", default="default", type=str, choices=["default", "small", "custom", "166"])
    args = parser.parse_args()
    process_id = args.process_id
    run_id = args.run_id
    mode = args.mode

    port_mapping = {"A": "50051", "B": "50052", "C": "50053"}
    peer_ports = [port_mapping[p] for p in port_mapping if p != process_id]
    all_ports = list(port_mapping.values())
    my_index = int(port_mapping[process_id]) % 50051

    num_to_port = {1: all_ports[(my_index)-2], 2: peer_ports[(my_index -1)]} # Maps action num to peer port to send to

    vm = VirtualMachine(process_id, port_mapping[process_id], num_to_port, run_id, port_mapping, mode)
    vm.run()
