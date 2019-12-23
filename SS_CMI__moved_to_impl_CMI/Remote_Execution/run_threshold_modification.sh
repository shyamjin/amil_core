#!/bin/bash

### This script wraps the threshold modification python script.
# For Value Pack, the following exported environment variables are required:
# - PYTHON_BIN_PATH
# - AMILY_SS_HOME
# - AMILY_VP_NEXUS_URL

echo "Connected to host: $(hostname)"
echo "Script: $0"

GENERATED_THR_DIR=${AMILY_SS_HOME}/Outbound_File_Transfer
CREATE_DU_SCRIPT=create_du.sh

rm -f ${GENERATED_THR_DIR:-MISSING_ENV_VAR_DEFINITION}/*.json

${PYTHON_BIN_PATH}/python -W ignore ${AMILY_SS_HOME}/atomIQ_ITSM_Self_Service-TH_Modification.pyc

cd ${GENERATED_THR_DIR:-MISSING_ENV_VAR_DEFINITION}

# ---- Upload to Value Pack as DU, if Value Pack is available
if [[ -n ${AMILY_SS_HOME} && -d ${AMILY_SS_HOME} && -n ${AMILY_VP_NEXUS_URL} ]]
then
    # Looks like this environment is configured for Value Pack
    echo "Pushing DU to Value Pack"
    RC=0

    # -- Test the Nexus connectivity
    curl ${AMILY_VP_NEXUS_URL} >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        # We have connectivity. Assume this Nexus URL is correct and valid.

        # -- Identify the filter types of the files (i.e. _ext_ or _int_)
        filename=$(ls *_thresholds*.json | head -1)
        filename_acct_prefix=${filename%_thresholds*.json}
        acct=${filename_acct_prefix//_/ }   # replace underscores with space
        ar_thres=$( echo $filename |sed 's/_thresholds//'|sed 's/.json$//')
        
        echo ".. Processing file ${filename}"

        # -- Run the create DU script
        dt_short=$(date +%Y%m%d%H%M)
        dt_long=$(date)
        artifact_name=${ar_thres}_Thresholds
        du_build_num=${dt_short}
        release_notes="Thresholds for ${acct} generated on ${dt_long}"
        file_list=${filename}

        ${AMILY_SS_HOME}/${CREATE_DU_SCRIPT} "${artifact_name}" "${du_build_num}" "${release_notes}" ${file_list}
        RC=$?

    else
        echo ".. ERROR: Unable to reach Nexus at ${AMILY_VP_NEXUS_URL}"
        RC=1
    fi
    # -- Check exit status
    if [[ $RC -ne 0 ]]
    then
        echo "There was an error. Exiting"
        exit 1
    fi
fi
