import grpc
from concurrent import futures
import time
import threading
import queue
import random
import logical_clock_pb2
import logical_clock_pb2_grpc

class ClockService(logical_clock_pb2_grpc.ClockServiceServicer):
    """Handles incoming messages and updates logical clock."""

    def __init__(self, process):
        self.process = process  # Reference to the main process object

    def SendMessage(self, request, context):
        """Handles received messages and places them in the event queue."""
        system_time = int(time.time())
        self.process.event_queue.put((request.sender_id, request.logical_clock, system_time))
        return logical_clock_pb2.Ack(message=f"Ack from {self.process.process_id}")

class VirtualMachine:
    """Represents a logical machine with a clock and gRPC server/client."""

    def __init__(self, process_id, port, peer_ports):
        self.process_id = process_id
        self.port = port
        self.peer_ports = peer_ports
        self.logical_clock = 0
        self.clock_rate = random.randint(1, 6)  # Random ticks per second
        self.event_queue = queue.Queue()
        self.log_file = f"{process_id}.log"

        # Start the gRPC server in a separate thread
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()

        time.sleep(2)  # Allow server to start before processing

    def start_server(self):
        """Initializes and starts the gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=3))
        logical_clock_pb2_grpc.add_ClockServiceServicer_to_server(ClockService(self), server)
        server.add_insecure_port(f"[::]:{self.port}")
        server.start()
        print(f"{self.process_id} Server started on port {self.port}...")
        server.wait_for_termination()

    def log_event(self, event_type, system_time, queue_length):
        """Logs all events in a single file per process."""
        with open(self.log_file, "a") as log:
            log.write(f"{event_type} | System Time: {system_time} | Queue: {queue_length} | LC: {self.logical_clock}\n")

    def process_message(self, sender_id, received_clock, system_time):
        """Processes a received message and updates logical clock."""
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
            system_time=int(time.time())
        )
        response = stub.SendMessage(message)
        print(f"{self.process_id} -> Sent message to {target_port} | LC: {self.logical_clock} | Response: {response.message}")

    def run(self):
        """Main event loop: process messages or generate events based on clock rate."""
        while True:
            time.sleep(1 / self.clock_rate)  # Simulate different speeds

            if not self.event_queue.empty():
                sender_id, received_clock, system_time = self.event_queue.get()
                self.process_message(sender_id, received_clock, system_time)
            else:
                action = random.randint(1, 10)
                if action == 1:  # Send to one machine
                    target = random.choice(self.peer_ports)
                    self.logical_clock += 1
                    self.send_message(target)
                    self.log_event(f"SEND {target}", time.time(), self.event_queue.qsize())

                elif action == 2:  # Send to another machine
                    target = random.choice(self.peer_ports)
                    self.logical_clock += 1
                    self.send_message(target)
                    self.log_event(f"SEND {target}", time.time(), self.event_queue.qsize())

                elif action == 3:  # Send to both machines
                    self.logical_clock += 1
                    for target in self.peer_ports:
                        self.send_message(target)
                    self.log_event("SEND ALL", time.time(), self.event_queue.qsize())

                else:  # Internal event
                    self.logical_clock += 1
                    self.log_event("INTERNAL", time.time(), self.event_queue.qsize())

if __name__ == "__main__":
    process_id = input("Enter Process ID (A, B, C): ")
    port_mapping = {"A": "50051", "B": "50052", "C": "50053"}
    peer_ports = [port_mapping[p] for p in port_mapping if p != process_id]

    vm = VirtualMachine(process_id, port_mapping[process_id], peer_ports)
    vm.run()
