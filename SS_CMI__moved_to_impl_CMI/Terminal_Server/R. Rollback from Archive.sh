wd=$(pwd)
keydir="${wd}/keys"

LOCAL_LOGFILE=${wd}/logs/rollback_from_archive_$(date +%Y%m%d-%H%M%S%Z)_${USERNAME}.txt

# Copy all terminal output to a log file
exec &> >(tee "${LOCAL_LOGFILE}")

ssh -i "${keydir}/rollback_from_archive" utsadmin@cmilinutsaiuat1
echo
echo "Finished. Press ENTER to close this window."
read
