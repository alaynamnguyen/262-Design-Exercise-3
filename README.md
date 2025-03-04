# To generate proto

python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. logical_clock.proto

# To run unit tests

pytest -p no:warnings test_logical_clock.py
