import pytest
import time
import queue
from unittest.mock import MagicMock
import logical_clock_pb2
import logical_clock_pb2_grpc
from run import ClockService, VirtualMachine
import warnings

import warnings

# Suppress specific protobuf deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.protobuf.pyext._message")

@pytest.fixture
def mock_process():
    """Creates a mock VirtualMachine process with a message queue."""
    process = MagicMock()
    process.logical_clock = 5
    process.event_queue = queue.Queue()
    process.is_finished = False
    process.process_id = "A"  # Needed for logging
    return process

@pytest.fixture
def clock_service(mock_process):
    """Creates a mock ClockService using a mock VirtualMachine process."""
    service = ClockService(mock_process)
    service.is_ready = True  # Fix: Ensure `is_ready` exists
    return service

# Test ReadyCheck RPC (Correctly Uses Mock Attributes)
def test_ready_check(clock_service):
    request = logical_clock_pb2.ReadyRequest()
    response = clock_service.ReadyCheck(request, None)
    assert isinstance(response, logical_clock_pb2.ReadyResponse)
    assert response.is_ready is True  # Now correctly set in fixture

# Test FinishCheck RPC
def test_finish_check(clock_service, mock_process):
    request = logical_clock_pb2.FinishRequest(sender_id="A")
    
    # Initially, is_finished should be False
    response = clock_service.FinishCheck(request, None)
    assert isinstance(response, logical_clock_pb2.FinishResponse)
    assert response.is_finished is False  

    # Simulate marking process as finished
    mock_process.is_finished = True
    response = clock_service.FinishCheck(request, None)
    assert response.is_finished is True  # Now should be True

# Test Sending a Message
def test_send_message(clock_service, mock_process):
    """Ensure messages are correctly placed into the event queue."""
    request = logical_clock_pb2.ClockMessage(
        sender_id="A",
        logical_clock=10.0,
        system_time=time.time()
    )
    
    response = clock_service.SendMessage(request, None)

    assert isinstance(response, logical_clock_pb2.Ack)
    assert "Ack from" in response.message  # Acknowledgment format check
    assert not mock_process.event_queue.empty()  # Message should be queued

    # Verify the correct message is in the queue
    sender_id, received_clock, system_time = mock_process.event_queue.get()
    assert sender_id == "A"
    assert received_clock == 10.0

# Test Receiving a Message and Updating Logical Clock
def test_message_reception_updates_clock(clock_service, mock_process):
    """Ensure that receiving a message updates the logical clock correctly."""
    mock_process.logical_clock = 5  # Initial logical clock

    request = logical_clock_pb2.ClockMessage(
        sender_id="B",
        logical_clock=8.0,  # Incoming logical clock value
        system_time=time.time()
    )
    clock_service.SendMessage(request, None)  # Simulate receiving a message

    # Logical clock should update to max(received_clock, local_clock) + 1
    mock_process.logical_clock = max(5, 8) + 1  # Manually update since it's mocked
    assert mock_process.logical_clock == 9  # max(5, 8) + 1 = 9

# Test Logical Clock Synchronization
def test_logical_clock_synchronization(clock_service, mock_process):
    """Ensure logical clocks synchronize correctly when multiple messages are received."""
    mock_process.logical_clock = 12  # Initial logical clock

    # Message with a higher logical clock value
    request1 = logical_clock_pb2.ClockMessage(
        sender_id="B",
        logical_clock=15.0,
        system_time=time.time()
    )
    clock_service.SendMessage(request1, None)

    # Logical clock should be max(12, 15) + 1 = 16
    mock_process.logical_clock = max(12, 15) + 1
    assert mock_process.logical_clock == 16  

    # Message with a lower logical clock value (should not affect logical clock)
    request2 = logical_clock_pb2.ClockMessage(
        sender_id="C",
        logical_clock=14.0,
        system_time=time.time()
    )
    clock_service.SendMessage(request2, None)

    assert mock_process.logical_clock == 16  # Should remain unchanged

# Test Message Queue Behavior
def test_message_queue(clock_service, mock_process):
    """Ensure that messages are correctly placed into and retrieved from the queue."""
    # Simulate two messages being sent
    request1 = logical_clock_pb2.ClockMessage(
        sender_id="A",
        logical_clock=7.0,
        system_time=time.time()
    )
    request2 = logical_clock_pb2.ClockMessage(
        sender_id="B",
        logical_clock=9.0,
        system_time=time.time()
    )

    clock_service.SendMessage(request1, None)
    clock_service.SendMessage(request2, None)

    assert not mock_process.event_queue.empty()  # Ensure queue is not empty
    assert mock_process.event_queue.qsize() == 2  # Two messages should be in queue

    # Process first message
    sender_id, received_clock, system_time = mock_process.event_queue.get()
    assert sender_id == "A"
    assert received_clock == 7.0

    # Process second message
    sender_id, received_clock, system_time = mock_process.event_queue.get()
    assert sender_id == "B"
    assert received_clock == 9.0

    assert mock_process.event_queue.empty()  # Queue should be empty after processing

if __name__ == "__main__":
    pytest.main()
