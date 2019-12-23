# This script executes the following steps:
#	[SS]               trigger model generation (interactive) and create DU
#	[TS]               clean up temp files
#
# Exact remote file/dir paths for SCP are defined in the ~/.ssh/authorized_keys file in the remote hosts


wd=$(pwd)
keydir="${wd}/keys"
LOCAL_FILE_XFER_DIR=/tmp/amily_ss_file_xfer
LOCAL_LOGFILE=${wd}/logs/model_generation_log_$(date +%Y%m%d-%H%M%S%Z)_${USERNAME}.txt

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

# --- Run the model generation script
echo -e "\n\n${ANSI_BLUE}# Train the model${ANSI_RESET}"
ssh -i "${keydir}/generate_model" ${USERHOST_CMI_SS}
if [[ $? -ne 0 ]]; then exit_with_error; fi

echo "Model DU is now created. Log into Value Pack eDPM to deploy it"

# --- Clean up local files
echo -e "\n\n${ANSI_BLUE}# Cleaning up local files on TS${ANSI_RESET}"
clean_local_files

exit_no_error
