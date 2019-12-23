#!/bin/bash

echo -e "\e[1;30m"
echo "Connected to host: $(hostname)"
echo "Script: $0"
echo -e "\e[0m"

PKL_DIR=/prjvl01/amily/Amily_Prod/Pickles
JSON_DIR=/prjvl01/amily/Amily_Prod/Configurations
ARCHIVE_DIR=/prjvl01/amily/Amily_Rollback/all
ARCHIVES_MD5_FILE=/dev/shm/archives.md5

# --- Backup everything in the Pickles and Configuration directory that doesn't already appear to be in the Rollback directory


function backup_new_files_to_archive
{
  originals_dir=$1
  file_ext=$2

  echo "Working on: ${originals_dir} / *${file_ext}"
  
  # -- Make md5 hash for all archived files
  echo "  Scanning the rollback archive directory"
  (cd ${ARCHIVE_DIR} ; md5sum *${file_ext}__[0-9]* ) > ${ARCHIVES_MD5_FILE} 2>/dev/null
  
  echo "  Comparing current files against the archive"
  total=0
  # -- Compare each current file to those in the archive
  for curr_file in $( cd ${originals_dir}; ls *${file_ext} )
  do
    md5_curr=$(cd ${originals_dir}; md5sum ${curr_file})
    if ( ! grep -q "${md5_curr}" ${ARCHIVES_MD5_FILE} )
    then
      # -- the current file was not present with the same md5 hash in the archives
      #    so add it now to the archives
  
      # create a datestamp of format YYYYMMDD_hhmm
      datestamp=$(stat -c %y ${originals_dir}/${curr_file} |sed 's/-//g;s/://g;s/ /_/'|cut -c1-13)
      echo "  .. archiving: ${curr_file}  [${datestamp}]"
      cp -p ${originals_dir}/${curr_file} ${ARCHIVE_DIR}/${curr_file}__${datestamp}
      let total+=1
    fi
  done
  
  rm ${ARCHIVES_MD5_FILE}
  
  echo "Backed up ${total} file(s)"
  echo
}

# --- MAIN ---

backup_new_files_to_archive ${PKL_DIR} ".pkl"
backup_new_files_to_archive ${JSON_DIR} ".json"

