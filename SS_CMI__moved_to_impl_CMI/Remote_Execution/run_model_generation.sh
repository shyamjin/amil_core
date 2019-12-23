#!/bin/bash

### This script wraps the model generation python script.
# For Value Pack, the following exported environment variables are required:
# - PYTHON_BIN_PATH
# - AMILY_SS_HOME
# - AMILY_VP_NEXUS_URL

echo -e '\e[1;30m'
echo "Connected to host: $(hostname)"
echo "Script: $0"
echo -e '\e[0m'
echo

ARCHIVE_DIR=${AMILY_SS_HOME}/Archive
MODEL_GEN_SCRIPT=${AMILY_SS_HOME}/atomIQ_ITSM_Self_Service-Classification_Module.pyc
GENERATED_PICKLES_DIR=${AMILY_SS_HOME}/Outbound_File_Transfer
CREATE_DU_SCRIPT=create_du.sh

# ---- STEP 1: Get the account name and dataset ID from the user

cat <<EOF
AVAILABLE ACCOUNTS
------------------
EOF
(cd ${ARCHIVE_DIR}; ls *txt | sed 's/--.*//' | uniq)

while true
do
  echo -n -e "\nEnter the account name\n--> "
  read acct   # Note: acct value may contain a space
  # Test if the chosen account if valid
  if ( cd ${ARCHIVE_DIR} ; ls | grep -q "^${acct}--.*.txt$"  )
  then
    break
  fi
  echo -e "\e[1;33mPlease select one of the available accounts listed above\e[0m"
done

days=7
while true
do
  echo -n -e "\nEnter the ID number of the labeling  (Press ENTER to see some options)\n--> "
  read label_id
  # -- Check if ID is a number
  if ( echo "$label_id" | grep -q '[^0-9]' )
  then
    echo -e "\e[1;33mID must be a number.\e[0m"
    continue
  fi

  # -- Try to resolve a existent filename
  label_filename=$(cd ${ARCHIVE_DIR} ; ls | grep "^${acct}--0*${label_id}.txt$")
  if [[ -n ${label_filename} ]] ; then break ; fi

  # -- below is error handling
  if [[ -n ${label_id} ]]
  then
    echo -e "\e[1;33mData for that ID is not available.\e[0m"
  fi
  echo "The following were generated in the past ${days} days:"
  find ${ARCHIVE_DIR} -maxdepth 1 -name "*.txt" -mtime -${days} -printf '%CY-%Cm-%Cd %CH:%CM  %f\n' | grep "  ${acct}--" | sort
  let days+=7
done

# ---- STEP 2: Invoke the model generator

rm -f ${GENERATED_PICKLES_DIR:-MISSING_ENV_VAR_DEFINITION}/*.pkl

echo -e '\e[1;30m${PYTHON_BIN_PATH}/python -W ignore "'${MODEL_GEN_SCRIPT}'" "'${ARCHIVE_DIR}/${label_filename}'" Deploy\e[0m'
${PYTHON_BIN_PATH}/python -W ignore "${MODEL_GEN_SCRIPT}" "${ARCHIVE_DIR}/${label_filename}" Deploy
if [[ $? -ne 0 ]]
then
  echo -e "\e[1;33mError executing training script.\e[0m"
  exit 1
fi

# ---- STEP 3: Prepare for file transfer
cd ${GENERATED_PICKLES_DIR:-MISSING_ENV_VAR_DEFINITION}

# ---- STEP 4: Upload to Value Pack as DU, if Value Pack is available
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
        echo ".. Processing account [${acct}]"
        dt_short=$(date +%Y%m%d%H%M)
        dt_long=$(date)
        cfn_filename=$(ls *_Classification_model*.pkl)
        artifact_name=$(echo ${cfn_filename}|sed 's/_Classification_model//;s/\.pkl//')_Model
        du_build_num=${dt_short}
        release_notes="Model for ${artifact_name} archived on ${dt_long}"
        nlp_filename=$(echo ${cfn_filename}|sed 's/_Classification_model/_NLP_Preprocessor/')
        file_list="${cfn_filename} ${nlp_filename}"
        echo ".. Processing files ["${file_list}"]"
        ${AMILY_SS_HOME}/${CREATE_DU_SCRIPT} "${artifact_name}" "${du_build_num}" "${release_notes}" ${file_list}
        RC=$?
        if [[ $RC -ne 0 ]]; then break; fi

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
