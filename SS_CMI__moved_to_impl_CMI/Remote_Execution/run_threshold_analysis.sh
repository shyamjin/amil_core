#!/bin/bash

### This script wraps the threshold analysis python script.
# For Value Pack, the following exported environment variables are required:
# - PYTHON_BIN_PATH
# - AMILY_SS_HOME

echo "Connected to host: $(hostname)"
echo "Script: $0"

${PYTHON_BIN_PATH}/python -W ignore ${AMILY_SS_HOME}/atomIQ_ITSM_Self_Service-TH_Analysis.pyc
