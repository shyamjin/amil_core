#!/usr/bin/env bash

# Script to handle install or uninstall of DU.
# This script will get embedded into the DU and invoked indirectly by the DPM.

# --- Identify the mode of operation
mode=$1
case ${mode} in
    install   )
        :  # do nothing
        ;;
    redeploy  )
        :  # do nothing
        ;;
    uninstall )
        :  # do nothing
        ;;
    * )
        echo "Usage: $0 {install|uninstall|redeploy}"
        exit 1
        ;;
esac

# --- Check for AMILY_WS_HOME location
# Note: DPM should be configured to execute the user's .profile before this script is invoked.

AMILY_WS_HOME=${AMILY_WS_HOME:-/prjvl01/amily/Amily_Prod}
if [[ ! -d ${AMILY_WS_HOME} ]]
then
    echo "Did not find Amily web service installed at ${AMILY_WS_HOME}"
    echo "or AMILY_WS_HOME environment variable is not set by .profile"
    echo "Exiting."
    exit 1
fi

# --- Let's see what files were in the DU package, which DPM already unzipped into the working directory
PKL_FILES=$(ls *.pkl 2>/dev/null)
THR_FILES=$(ls *thresholds*.json 2>/dev/null)

if [[ -n "${PKL_FILES}" ]]
then
    target_dir="${AMILY_WS_HOME}/Pickles"
    file_list=${PKL_FILES}
elif [[ -n "${THR_FILES}" ]]
then
    target_dir="${AMILY_WS_HOME}/Configurations"
    file_list=${THR_FILES}
fi

case ${mode} in
    install | redeploy )
        if [[ ! -d ${target_dir} ]]
        then
            echo "[${target_dir}] directory not found! Exiting."
            exit 1
        fi

        cp -v ${file_list} "${target_dir}"
        RC=$?
        ;;

    uninstall )
        cd ${target_dir} \
        && rm -v ${file_list}
        RC=$?
        ;;
esac

# --- Handle errors
if [[ ${RC} -ne 0 ]]
then
    echo "ERROR: Failed to process the files in the DU"
    exit 1
fi

# --- All done
echo "Done."
exit 0