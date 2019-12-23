#!/bin/bash

echo -e "\e[1;30m"
echo "Connected to host: $(hostname)"
echo "Script: $0"
echo -e "\e[0m"

PKL_DIR=/prjvl01/amily/Amily_Prod/Pickles
JSON_DIR=/prjvl01/amily/Amily_Prod/Configurations
ARCHIVE_DIR=/prjvl01/amily/Amily_Rollback/all
ARCHIVES_MD5_FILE=/dev/shm/archives.md5

ANSI_BRIGHT_WHITE="\e[1;37m"
ANSI_BRIGHT_BLACK="\e[1;30m"
ANSI_BRIGHT_RED="\e[1;31m"
ANSI_BRIGHT_GREEN="\e[1;32m"
ANSI_BRIGHT_YELLOW="\e[1;33m"
ANSI_RESET="\e[0m"

echo "Rollback from archive"
echo

while true
do
  echo -e "Do you want to rollback the ${ANSI_BRIGHT_WHITE}model${ANSI_RESET} or the ${ANSI_BRIGHT_WHITE}thresholds${ANSI_RESET}?"
  echo -n "-> "
  read x
  if [[ ${x} =~ mod.* ]]
  then
    target_dir=${PKL_DIR}
    file_ext=.pkl
    break
  fi
  if [[ ${x} =~ thr.* ]]
  then
    target_dir=${JSON_DIR}
    file_ext=.json
    break
  fi
done

# -- create a list of account names. $accounts_list is newline-delimited if double-quoted
if   [[ ${file_ext} = ".pkl" ]]
then
  accounts_list="$(cd ${ARCHIVE_DIR};ls *${file_ext}__*|sed 's/_Dispatch_.*\|_int_.*\|_ext_.*//'|sort|uniq)"
elif [[ ${file_ext} = ".json" ]]
then
  accounts_list="$(cd ${ARCHIVE_DIR};ls *_thresholds${file_ext}__*|sed 's/_thresholds\..*//'|grep -v _dispatch|sort|uniq)"
else
  accounts_list="$(cd ${ARCHIVE_DIR};ls *${file_ext}__*|sed 's/'${file_ext}'.*//'|sort|uniq)"
fi

echo
echo "Rollback is available for the following accounts:"
echo "${accounts_list}"|sed 's/^/  /g'
echo

while true
do
  echo "Enter the account name as shown in the list above (at least the start of the name)"
  echo -n "-> "
  read x
  # check if the selection is uniq in the list
  match_count=$(echo "${accounts_list}"|grep -i "^$x"|wc -l)
  if [[ ${match_count} -eq 1 ]]
  then
    acct=$(echo "${accounts_list}"|grep -i "^$x")
    break
  fi
done

echo "$acct"
echo

if [[ ${file_ext} = .pkl ]]
then
  while true
  do
    echo -e "${ANSI_BRIGHT_WHITE}Internal${ANSI_RESET} or ${ANSI_BRIGHT_WHITE}External${ANSI_RESET} model?"
    echo -n "-> "
    read x
    if   [[ ${x,,} =~ int.* ]]
    then
      mtype=int
      break
    elif [[ ${x,,} =~ ext.* ]]
    then
      mtype=ext
      break
    fi
  done
fi
echo

if   [[ ${file_ext} = ".pkl" ]]
then
  datetime_list="$(cd ${ARCHIVE_DIR};ls ${acct}_${mtype}_*${file_ext}__*|sed 's/.*__//'|sort|uniq)"
elif [[ ${file_ext} = ".json" ]]
then
  datetime_list="$(cd ${ARCHIVE_DIR};ls ${acct}_thresholds${file_ext}__*|sed 's/.*__//'|sort|uniq)"
fi

echo "Available dates times for rollback to:"
echo "$datetime_list"|sed 's/\(....\)\(..\)\(..\)_\(..\)\(..\)/\1-\2-\3 \4:\5/; s/^/  /g'
echo

while true
do
  echo "Enter the date + time stamp you want to roll back to"
  echo -n "-> "
  read x
  # Convert datetime format from YYYY-MM-DD hh:mm to YYYYMMDD_hhmm
  x=${x//-/}  # remove dashes
  x=${x// /_} # replace space with underscore
  x=${x//:/}  # remove colons

  # check if the selection is uniq in the list
  match_count=$(echo "${datetime_list}"|grep -i "^$x"|wc -l)
  if [[ ${match_count} -eq 1 ]]
  then
    datetime=$(echo "${datetime_list}"|grep -i "^$x")
    rdate=${datetime%_*}  # remove stuff after the _
    rtime=${datetime#*_}  # remove stuff before the _
    rdate=${rdate:0:4}-${rdate:4:2}-${rdate:6:2}  # insert dash between YYYY MM DD
    rtime=${rtime:0:2}:${rtime:2:2}  # insert colon between HH and MM
    break
  fi
done

echo "$rdate $rtime"
echo

if   [[ ${file_ext} = ".pkl" ]]
then
  file_list="$(cd ${ARCHIVE_DIR};ls ${acct}_${mtype}_*${file_ext}__${datetime})"
elif [[ ${file_ext} = ".json" ]]
then
  file_list="$(cd ${ARCHIVE_DIR};ls ${acct}_thresholds${file_ext}__${datetime})"
fi

echo "Checking..."
all_same=1
for f in ${file_list}
do
  f2=${f%__*}	# remove the datestamp suffix
  echo -e "${ANSI_BRIGHT_BLACK}.. ${f}${ANSI_RESET}"
  diff -q ${ARCHIVE_DIR}/${f} ${target_dir}/${f2} >/dev/null
  if [[ $? -ne 0 ]]
  then
    all_same=0
    break
  fi
done

if [[ ${all_same} -eq 1 ]]
then
  echo -e "${ANSI_BRIGHT_YELLOW}The currently deployed files are the same as the rollback you selected!${ANSI_RESET}"
  echo
  echo "Rollback skipped."
  echo
  exit 0
fi

echo
echo "Rolling back from the following files:"
echo "  Account:     ${acct}"
echo "  Model Type:  ${mtype}"
echo "  Date & Time: ${rdate} ${rtime}"
echo

while true
do
  echo -e "Please confirm (${ANSI_BRIGHT_WHITE}Y${ANSI_RESET}/${ANSI_BRIGHT_WHITE}n${ANSI_RESET})"
  echo -n "-> "
  read x
  if   [[ ${x} =~ "Y" ]]
  then
    break
  elif [[ ${x} =~ "n" ]]
  then
    echo -e "${ANSI_BRIGHT_YELLOW}Aborted by user${ANSI_RESET}"
    exit 0
  fi
done
echo

echo "Performing rollback..."
for f in ${file_list}
do
  f2=${f%__*}	# remove the datestamp suffix
  echo -n -e "${ANSI_BRIGHT_BLACK}"
  echo -n ".. "
  cp -v ${ARCHIVE_DIR}/${f} ${target_dir}/${f2}
  RC=$?
  echo -n -e "${ANSI_RESET}"
  if [[ $RC -ne 0 ]]
  then
    echo -e "${ANSI_BRIGHT_RED}Copy failed!! Aborting rollback.${ANSI_RESET}"
    exit 1
  fi
done

echo
echo -e "${ANSI_BRIGHT_GREEN}Rollback completed${ANSI_RESET}"

