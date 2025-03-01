# To generate proto

python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. logical_clock.proto
