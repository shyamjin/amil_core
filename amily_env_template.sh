### This file defines environment-specific settings for Amily, as exported shell environment variables.

#-- Path of the Python3 'bin' directory
export PYTHON_BIN_PATH=


#-- Amily top level home
export AMILY_HOME=


#-- Amily Web Service

# Top level directory path for Amily web service
export AMILY_WS_HOME=

# Full path to logs directory
export AMILY_WS_LOGS_DIR=

# Web server listen port (https)
export AMILY_WS_HTTPS_LISTEN_PORT=

# Linux service PID file
export AMILY_WS_PID_PATH=${AMILY_WS_HOME}/amilyws.pid


#-- Web Service security settings
#   The following files must exist under the 'SSL' directory

# Password file for HTTP Basic Authentication
export AMILY_WS_PASSWD_FILENAME=default.htpasswd

# PEM-encoded X.509 certificate
export AMILY_WS_CERT_FILENAME=default.crt

# PEM-encoded private key for the certificate
export AMILY_WS_CERT_PRIVATEKEY_FILENAME=default.key


#-- Amily Self Service paths

# Top level directory path for Amily self service
export AMILY_SS_HOME=

# Full path to logs directory for self service
export AMILY_SS_LOGS_DIR=


#-- Value Pack environment

# Record if sudo was needed for installation (do not edit manually)
export AMILY_VP_INSTALLED_WITH_SUDO=
# The below are required for creating a DU build
export AMILY_VP_NEXUS_URL=http://vp_nexus_public_host_name:8081/nexus
export AMILY_VP_NEXUS_USER=xxxx
export AMILY_VP_NEXUS_PASS=xxxx
export AMILY_VP_NEXUS_REPO=vp_builds
export AMILY_VP_NEXUS_GROUP=amdocs.aio.atomiq_ticketing_du
export AMILY_DPM_BASE_URL=https://vp_dpm_public_host_name:8000
export AMILY_DPM_AUTH_TOKEN=xxxx


#-- Source the Implementation layer env file
if [[ -f ${AMILY_HOME}/amily_env_impl.sh ]]
then
    . ${AMILY_HOME}/amily_env_impl.sh
fi