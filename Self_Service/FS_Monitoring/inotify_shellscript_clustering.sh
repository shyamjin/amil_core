#!/bin/bash
watchdir=/UTSAmilyAttachments/UTS_TO_AMILY/Clustering/

if [[ -z ${AMILY_SS_HOME} ]]
then
    echo "Environment variable [AMILY_SS_HOME] is not set. Exiting!"
    exit 1
fi

if [[ -z ${AMILY_SS_LOGS_DIR} ]]
then
    echo "Environment variable [AMILY_SS_LOGS_DIR] is not set. Exiting!"
    exit 1
fi

if [[ -z ${PYTHON_BIN_PATH} ]]
then
    echo "Environment variable [PYTHON_BIN_PATH] is not set. Exiting!"
    exit 1
fi

logfile=${AMILY_SS_LOGS_DIR}/inotify_watchlog.txt

while : ; do
        inotifywait -m $watchdir -e CREATE|
			while read path action file; do
                ts=$(date +"%C%y%m%d%H%M%S")
                echo "$ts :: file: $file :: $action :: $path">>$logfile
				${PYTHON_BIN_PATH}/python -W ignore ${AMILY_SS_HOME}/atomIQ_ITSM_Self_Service-Clustering_Module.pyc $watchdir"$file"
        done
done
exit 0
