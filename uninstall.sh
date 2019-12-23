#!/usr/bin/env bash
# Uninstall Amily (AtomIQ Ticketing) core layer

# The goals of the script are
# - Stop the web server if it was running
# - Stop the inotify processes if any were running
# - Remove only files that were installed from the core.
#   .. If there's anything else in the runtime, then leave it behind.
#   .. For example: IMPL layer files, log files, manual changes to core files
#   .. Note: IMPL should be uninstalled independently (and ideally, before core)
# - amily env file (amily_env.sh) will be removed ONLY if it is the last thing left in the AMILY_HOME.
#   .. Reason: if you have IMPL installed, you probably are going to reinstall core, and want to keep the environment configs like passwd and certificates.
# - If amily env file was removed (because it was the last thing left), then remove the AMILY_HOME also.
#   .. This is supposed to be a real cleanup.
#   .. This will happen if someone installed core and uninstalled right away.
# - Clean up the ~/.profile if the AMILY_HOME is removed
#   .. (the Amily installer created/modified the .profile, to invoke the amily env file)
# - Remove the web service start/stop script

#-- Global script constants
AMILY_WS_STARTSTOP_SCRIPT=${AMILY_WS_HOME}/amilyws.sh
AMILY_INITD_SCRIPT=/etc/rc.d/init.d/amily
INOTIFY_PROCESS_NAME_PATTERN='inotify_shellscript_'
ENV_FILENAME=amily_env.sh

#-- Dynamic vars for the script
SUDO=                           # the 'sudo' command to use. Default is blank -> don't sudo
error_count=0
warning_count=0

# ... Assume the .profile has been invoked and environment like AMILY_HOME has been set

#-- Validate environment
if [[ -z ${AMILY_HOME} ]]
then
    echo "AMILY_HOME is not set. Cannot proceed with uninstall"
    exit 1
fi

echo "AMILY_HOME is [${AMILY_HOME}]"
echo

#-- If needing to 'sudo', then restart the whole script as sudo
if [[ ${VP_INSTALLED_WITH_SUDO} = TRUE && $(id -u) != 0 ]]
then
    echo ">>> Switching to user root for uninstall"
    sudo $0 $@
    exit $?
    #-- the script terminates here --#
fi

#-- Stop Amily web service
echo "Stopping Amily web service"
echo ".. ${AMILY_WS_STARTSTOP_SCRIPT} stop"
${AMILY_WS_STARTSTOP_SCRIPT} stop
echo

#-- Stop inotify processes
echo "Stopping inotify processes"
ps_list="$(ps -ef|grep ${INOTIFY_PROCESS_NAME_PATTERN}|grep -v grep\ ${INOTIFY_PROCESS_NAME_PATTERN})"
if [[ -n ${ps_list} ]]
then
    echo ".. found the following processes:"
    echo "${ps_list}"
    echo ".. killing now:"
    pkill -e -f "${INOTIFY_PROCESS_NAME_PATTERN}"
else
    echo ".. did not find any inotify processes"
fi
echo

#-- Remove only the files and directories that are included in the installation package
#   (we assume that DPM is invoking the uninstall.sh from the exploded zip file that was used for installation)

# The following 'find' command removes all files in the runtime area that are common to the staging area.
# It embeds the 'cmp' command, such that runtime files which are different in content to the staging area (even with
# the same filename) will NOT be deleted.
# This process will cause the amily env.sh file and log files to remain, as well as any files added/changed manually
# since installation, including IMPL layer files which were not part of the core layer.

echo "Uninstalling the Amily core layer"

#-- Uninstall amily service start/stop script
if [[ -f ${AMILY_INITD_SCRIPT} ]]
then
    echo "Removing amily service start/stop script in /etc/rc.d/init.d"
    sudo rm -vf ${AMILY_INITD_SCRIPT:-AMILY_INITD_SCRIPT_NOT_DEFINED}         || let error_count+=1
fi
echo


staging_dir=$(pwd)
cd ${AMILY_HOME}
echo "   Directory is: $(pwd)"
find -type f -exec cmp -s {} ${staging_dir}/{} \; -printf ".. removing file %p\n" -delete  || let error_count+=1
# remove other stuff added by in by the install process itself
find -type f -name build_info_core.txt -printf ".. removing file %p\n" -delete  || let error_count+=1
find ./Amily_Prod -maxdepth 1 -type f -name amily -printf ".. removing file %p\n" -delete  || let error_count+=1
rm -vf ${AMILY_WS_PID_PATH:-AMILY_WS_PID_PATH_NOT_DEFINED}          || let error_count+=1

# Remove any empty directories
find -type d -empty -printf ".. removing directory %p\n" -delete    || let error_count+=1

# If web service and self service have been completely removed, them do more cleanup
if [[ ! -d ${AMILY_WS_HOME} && ! -d ${AMILY_SS_HOME} ]]
then
    # also remove the amily_env.sh file
    find -type f -name ${ENV_FILENAME} -printf ".. removing file %p\n" -delete  || let error_count+=1
fi

# Is everything totally gone now?
if [[ $( find . | wc -l ) -eq 1 ]]
then
    # Yes!
    # now remove the AMILY_HOME directory itself.
    cd - >/dev/null    # we need to first jump out of the AMILY_HOME dir in order to delete it
    find ${AMILY_HOME:-SOMETHING_WENT_WRONG} -type d -empty -printf ".. removing directory %p\n" -delete    || let error_count+=1
    echo
else
    echo
    echo "The following files remain:"
    find -type f -printf "   %p\n"
    cd - >/dev/null
fi

# remove amily_env.sh from .profile
echo "Disabling the loading of Amily environment in ~/.profile"
perl -i -p -e 's/^(. $ENV{"AMILY_HOME"}\/$ENV{"ENV_FILENAME"})/## REMOVED ## $1/'  ~/.profile   || let error_count+=1

echo

#-- Finish up
if [[ ${error_count} -ne 0 ]]
then
    echo "!!! There were errors during deployment"
    exit 1
fi

case ${warning_count} in
    0)
        echo "--- Uninstall completed successfully."
        ;;
    1)
        echo "*** Uninstall completed WITH 1 WARNING"
        ;;
    *)
        echo "*** Uninstall completed WITH ${warning_count} WARNINGS"
        ;;
esac

exit 0
