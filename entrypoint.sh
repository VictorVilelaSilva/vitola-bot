#!/bin/bash

# Activate the virtual environment
source /opt/app/venv/bin/activate

# Execute the command passed to the entrypoint (e.g., "python main.py")
exec "$@"