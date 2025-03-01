import grpc
from concurrent import futures
import time
import logical_clock_pb2
import logical_clock_pb2_grpc

class MessengerServicer(logical_clock_pb2_grpc.MessengerServicer):
    def SendMessage(self, request_iterator, context):
        for message in request_iterator:
            print(f"Received from {message.sender}: {message.content}")
            yield logical_clock_pb2.Message(sender="Server", content=f"Acknowledged: {message.content}")

def start_server(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=3))
    logical_clock_pb2_grpc.add_MessengerServicer_to_server(MessengerServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Server listening on port {port}...")
    server.wait_for_termination()

if __name__ == "__main__":
    import sys
    port = sys.argv[1] if len(sys.argv) > 1 else "50051"
    start_server(port)
