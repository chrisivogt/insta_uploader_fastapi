#!/bin/bash

# Ensure the script stops if any command fails
set -e

# Run Uvicorn using the python module approach
# --host 0.0.0.0 is REQUIRED for containers to accept traffic from outside
exec /root/main/bin/python3 -m uvicorn fastapiapp:app --host 0.0.0.0 --port 8000
