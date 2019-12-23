#!/bin/bash

echo -e "\e[1;30m"
echo "Connected to host: $(hostname)"
echo "Script: $0"
echo -e "\e[0m"
echo

SCP_DIR=/dev/shm
PROD_DIR=/prjvl01/amily/Amily_Prod/Pickles
CHECKSUM_FILENAME=pickles.md5

function fatal_error
{
  msg=$@
  echo -e "\e[1;33m${msg}\e[0m"
  exit 1
}

function backup_live_files
{
  cat ${SCP_DIR}/${CHECKSUM_FILENAME} | while read checksum filename
  do
    # -- only make a backup if the original file exists!
    if [[ -f ${PROD_DIR}/${filename} ]]
    then
      cp -f ${PROD_DIR}/${filename} ${PROD_DIR}/${filename}.bak || fatal_error "Failed to create backup of the live file ${PROD_DIR}/${filename}"
    fi
  done
}

function rollback_live_files
{
  cat ${SCP_DIR}/${CHECKSUM_FILENAME} | while read checksum filename
  do
    # -- only restore files where the backup exists, assuming that the only reason for no backup file is because there was no original file
    if [[ -f ${PROD_DIR}/${filename}.bak ]]
    then
      mv ${PROD_DIR}/${filename}.bak ${PROD_DIR}/${filename} || fatal_error "Failed to restore live file from backup: ${PROD_DIR}/${filename}"
    fi
  done
  echo "Rollback completed"
}

function remove_backup_files
{
  cat ${SCP_DIR}/${CHECKSUM_FILENAME} | while read checksum filename
  do
    if [[ -f ${PROD_DIR}/${filename}.bak ]]
    then
      rm ${PROD_DIR}/${filename}.bak || echo -e "\e[0;33mWARNING: Failed to remove no-longer-needed backup of the live file ${PROD_DIR}/${filename}.bak\e[0m"
    fi
  done
}

echo "Validating the file transfer"

# -- Check the checksum file exists
if [[ ! -f ${SCP_DIR}/${CHECKSUM_FILENAME} ]]
then
  fatal_error "MD5 hash file is missing. Cannot validate the file transfer"
fi

# -- Check each file listed in the checksum file
(cd ${SCP_DIR}; md5sum --check ${CHECKSUM_FILENAME}) || fatal_error "Checksum check failed!"

echo
echo

# -- Move the files to the production directory
echo "Moving the files to the web service path on this server"

echo ".. doing backup"
backup_live_files

echo ".. moving files"
cat ${SCP_DIR}/${CHECKSUM_FILENAME} | while read checksum filename
do
  # -- first backup the live file
  mv ${SCP_DIR}/${filename} ${PROD_DIR}/${filename}
  if [[ $? -ne 0 ]]
  then
    # -- try to recover the backup file
    echo -e "\e[1;31mFile move failed! Attempting to roll back...\e[0m"
    rollback_live_files
    fatal_error "Aborting due to failure copying files"
##TO DO: WHY IS THIS NOT EXITING WITH RC=1 ???
  fi
done

echo ".. removing backup"
remove_backup_files

echo ".. All done!"

exit 0
