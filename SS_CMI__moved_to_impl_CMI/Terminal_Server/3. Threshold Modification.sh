# This script executes the following steps:
# 	[UAT]->[TS]	pull all TH JSON files
# 	[TS]->[SS]	push all TS JSON files to 'Inbound_File_Transfer' dir
# 	[SS]		trigger TH configuration script (interactive) and create DU
# 	[TS]		clean up temp files from TS
#
# Exact remote file/dir paths for SCP are defined in the ~/.ssh/authorized_keys file in the remote hosts


wd=$(pwd)
keydir="${wd}/keys"
LOCAL_FILE_XFER_DIR=/tmp/amily_ss_file_xfer
LOCAL_LOGFILE=${wd}/logs/threshold_modification_log_$(date +%Y%m%d-%H%M%S%Z)_${USERNAME}.txt

USERHOST_CMI_DEV=amilydevc@cmilinutsaidev01
USERHOST_CMI_UAT=amily@cmilinutsaiuat1
USERHOST_CMI_SS=amily@cmilinutsaiprd3

#-#-# override!! #-#-#
#USERHOST_CMI_SS=amilydevc@cmilinutsaidev01

ANSI_BLUE="\e[0;34m"
ANSI_RESET="\e[0m"

function exit_with_error
{
    clean_local_files_force
    echo -e "\e[1;31m]There was an error.\e[0m"
    echo -e "\e[1;30mPress ENTER to close this window.\e[0m"
    read
    exit 1
}

function exit_no_error
{
    clean_local_files_force
    echo -e "${ANSI_RESET}Press ENTER to close this window.${ANSI_RESET}"
    read
    exit 0
}

function clean_local_files
{
    if [[ -z ${LOCAL_FILE_XFER_DIR} ]] ; then exit_with_error; fi
    if [[ -d ${LOCAL_FILE_XFER_DIR} ]]
    then
        rm -f ${LOCAL_FILE_XFER_DIR:-DONTDELETEROOT}/*  || exit_with_error
    else
        mkdir -p ${LOCAL_FILE_XFER_DIR} || exit_with_error
    fi
}

function clean_local_files_force
{
return
    if [[ -z ${LOCAL_FILE_XFER_DIR} ]] ; then exit 1; fi
    if [[ -d ${LOCAL_FILE_XFER_DIR} ]]
    then
        rm -f ${LOCAL_FILE_XFER_DIR:-DONTDELETEROOT}/*
        rmdir ${LOCAL_FILE_XFER_DIR}
    fi
}


# Copy all terminal output to a log file
exec &> >(tee "${LOCAL_LOGFILE}")


# --- Clean up local files
echo -e "\n\n${ANSI_BLUE}# Cleaning up local files on TS${ANSI_RESET}"
clean_local_files

# --- Pull old threshold files from UAT
echo -e "\n\n${ANSI_BLUE}# Pulling old threshold files to TS${ANSI_RESET}"
scp -i "${keydir}/pull_old_th"    ${USERHOST_CMI_UAT}:     ${LOCAL_FILE_XFER_DIR}
if [[ $? -ne 0 ]]; then exit_with_error; fi

th_file_name=\*_thresholds\*.json
th_file_path=${LOCAL_FILE_XFER_DIR}/${th_file_name}

# --- Push selected file to Self Service
echo -e "\n\n${ANSI_BLUE}# Pushing chosen threshold file to SS${ANSI_RESET}"
scp -i "${keydir}/push_old_th"    ${th_file_path}          ${USERHOST_CMI_SS}:
if [[ $? -ne 0 ]]; then exit_with_error; fi

# --- Run the threshold modification script
echo -e "\n\n${ANSI_BLUE}# Run Threshold Modification script${ANSI_RESET}"
ssh -i "${keydir}/th_modification" ${USERHOST_CMI_SS}
if [[ $? -ne 0 ]]; then exit_with_error; fi

echo "Threshold DU is now created. Log into Value Pack eDPM to deploy it"

# --- Clean up local files
echo -e "\n\n${ANSI_BLUE}# Cleaning up local files on TS${ANSI_RESET}"
clean_local_files

exit_no_error
