#!/bin/bash

### This script creates a set of DUs from thresholds and pickles currently on the filesystem.
#   The purpose is to bootstrap the DUs in VP in order that newer DUs can be rolled back if needed.
# For Value Pack, the following exported environment variables are required:
# - AMILY_SS_HOME
# - AMILY_VP_NEXUS_URL

echo -e '\e[1;30m'
echo "Connected to host: $(hostname)"
echo "Script: $0"
echo -e '\e[0m'
echo

PICKLES_DIR=${AMILY_WS_HOME}/Pickles
THRESHOLDS_DIR=${AMILY_WS_HOME}/Configurations
CREATE_DU_SCRIPT=${AMILY_SS_HOME}/create_du.sh

# Capture the current date & time
dt_short=$(date +%Y%m%d%H%M)
dt_long=$(date)

echo "Pushing DUs to Value Pack"
echo
RC=0
error_count=0

# -- Test the Nexus connectivity
curl ${AMILY_VP_NEXUS_URL} >/dev/null 2>&1
if [[ $? -eq 0 ]]
then
    # We have connectivity. Assume this Nexus URL is correct and valid.

    # -- Process the threshold files
    echo "Processing Thresholds files"
    cd ${THRESHOLDS_DIR}
    filenames=$(ls *_thresholds*.json)
    for filename in ${filenames}
    do
        filename_acct_prefix=${filename%_thresholds*.json}
        acct=${filename_acct_prefix//_/ }   # replace underscores with space
        ar_thres=$( echo $filename |sed 's/_thresholds//'|sed 's/.json$//')
        echo ".. Processing file ${filename}"

        # -- Run the create DU script
        artifact_name=${ar_thres}_Thresholds
        du_build_num=${dt_short}
        release_notes="Thresholds for ${acct} archived on ${dt_long}"
        file_list=${filename}

        ${CREATE_DU_SCRIPT} "${artifact_name}" "${du_build_num}" "${release_notes}" ${file_list}
        RC=$?

        if [[ ${RC} -ne 0 ]]
        then
            echo "ERROR: failed to upload a DU!"
            let error_count+=1
        fi

        echo
    done

    echo
    echo

    # -- Process the model files
    echo "Processing model files"
    cd ${PICKLES_DIR}
    filenames=$(ls *_Classification_model*.pkl)
    for cfn_filename in ${filenames}
    do

        artifact_name=$(echo ${cfn_filename}|sed 's/_Classification_model//;s/\.pkl//')_Model
        du_build_num=${dt_short}
        release_notes="Model for ${artifact_name} archived on ${dt_long}"
        nlp_filename=$(echo ${cfn_filename}|sed 's/_Classification_model/_NLP_Preprocessor/')
        file_list="${cfn_filename} ${nlp_filename}"
        echo ".. Processing files ${file_list}"

        # -- Run the create DU script
        ${CREATE_DU_SCRIPT} "${artifact_name}" "${du_build_num}" "${release_notes}" ${file_list}
        RC=$?

        if [[ ${RC} -ne 0 ]]
        then
            echo "ERROR: failed to upload a DU!"
            let error_count+=1
        fi

        echo
    done





else
    echo ".. ERROR: Unable to reach Nexus at ${AMILY_VP_NEXUS_URL}"
    let error_count+=1
fi

# -- Check exit status
if [[ ${error_count} -ne 0 ]]
then
    echo "There was an error. Exiting"
    exit 1
fi
