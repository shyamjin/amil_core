#!/bin/bash
#
# Amily web service start/stop/status script.
#
# Assumes the amily env has already been loaded into the shell environment
# i.e. ${AMILY_WS_HOME}, ${PYTHON_BIN_PATH}, etc.


command=$1  # This is the command 'start','stop', etc.

#-- Set the location of the pid path (the file that holds the PID of the running web server).
pid_path=${AMILY_WS_PID_PATH:-${AMILY_WS_HOME}/amilyws.pid}

prog="Amily web service"
RETVAL=1


start() {
        echo "Starting $prog: "

        # Check if Amily WS is already running
        if [ -e $pid_path ] && ps -p `cat $pid_path` >/dev/null
	    then
            echo "Amily web service is already running on pid `cat $pid_path`"
            return 0
	    fi

        #-- Check the Python binaries path
        if [[ -z ${PYTHON_BIN_PATH} ]]
        then
            echo "PYTHON_BIN_PATH is not defined! Cannot start Amily service!"
            exit 1
        fi

        PYTHON_CMD="${PYTHON_BIN_PATH}/python -W ignore"

        # Start the web service in the background
        nohup $PYTHON_CMD "${AMILY_WS_HOME}/Amily_web_service.pyc" >/dev/null 2>&1 &
        RC=$?
        echo $! > $pid_path

        RETVAL=${RC}
        return $RETVAL
}


stop() {
        echo "Shutting down $prog: "
        if [ -e $pid_path ]
	    then
	      kill -2 `cat $pid_path`
	      rm $pid_path
	    fi
	sleep 4
	RETVAL=0
	return $RETVAL
}

status() {
        echo "Checking $prog status: "
        if [ -e $pid_path ]; then RETVAL=0; else RETVAL=1
	fi
	echo $RETVAL
        return $RETVAL
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        stop
        start
        ;;
    *)
        echo "Usage: $prog {start|stop|status|restart}"
        exit 1
        ;;
esac
exit $RETVAL
