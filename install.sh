#!/usr/bin/env bash

# Install Amily (AtomIQ Ticketing) core layer
#
# The following environment variables should be passed (exported) by DPM before invoking this script:
# COMPONENTS    - comma-delimited list of components of Amily to be installed. These are set in the DPM 'tool' configuration.
#                 Values: WebService; SelfServce; DevTools;
# OPTIONS       - comma-delimited list of options requested by the user. These are set in the DPM 'tool' configuration
#                 Values: InstallAsRoot; InstallLinuxServce; SetVPEndpoints; SetWebServiceAuth; SetWebServiceCertificate
# PYTHON_BIN_PATH     - full path to the Python3 bin directory
# AMILY_HOME          - the file system path where Amily will be installed
# AMILY_WS_LOGS_DIR   - (optional) the full path to the Amily web service logs directory
# AMILY_SS_LOGS_DIR   - (optional) the full path to the Amily self-service logs directory
# AMILY_WS_HTTPS_PORT - (optional) the TCP port number that Amily web service will listen on
# AMILY_WS_USERNAME   - (optional) used to set the .htpasswd if OPTIONS contains SetWebServiceAuth
# AMILY_WS_PASSWORD   - (optional) used to set the .htpasswd if OPTIONS contains SetWebServiceAuth
# AMILY_WS_FRONTEND_HOST - (optional) used to generate the self-signed certificate, if OPTIONS contains SetWebServiceCertificate
#  - the following optional values are used if OPTIONS contains SetVPEndpoints
#    VP_NEXUS_HOST
#    VP_NEXUS_PORT
#    VP_NEXUS_USER
#    VP_NEXUS_PASS
#    VP_DPM_HOST
#    VP_DPM_PORT
#    VP_DPM_AUTH_TOKEN

SOURCE_DIR=`pwd`        # This is where DPM unzipped the tool package zip file


##==== SCRIPT VARIABLES INITIALIZATION ====

#-- Constants
ENV_FILENAME=amily_env.sh
ENV_TEMPLATE_FILENAME=amily_env_template.sh
BUILDINFO_FILE=build_info_core.txt
CREATE_WS_PASSWD_FILE_SCRIPT=create_ws_passwd_file.pyc

#-- Dynamic vars for the script
SUDO=                           # the 'sudo' command to use. Default is blank -> don't sudo
error_count=0
warning_count=0


# ==== SCRIPT FUNCTIONS ====
function add_or_update_env_var
{
    # Add or update a shell variable export declaration in the env.sh ($ENV_FILENAME} file
    # Input parameters:
    # 1. mode: 0=keep existing value if present & not null, otherwise add/update; 1=replace
    # 2. file name to modify (full path)
    # 3. name of env variable
    # 4. new value to set

    mode=$1
    envfile=$2
    varname=$3
    newvalue=$4

    if [[ ! -f ${envfile} ]]
    then
        echo "Environment: Creating new file: ${envfile}"
        touch ${envfile}
        if [[ $? -ne 0 ]]
        then
            echo "FATAL ERROR: cannot create file ${envfile}"
            exit 1
        fi
    fi

    if ( grep -q "^export ${varname}=" ${envfile} )
    then
        var_already_declared=1
    else
        var_already_declared=0
    fi

    if ( grep -q "^export ${varname}=." ${envfile} )
    then
        var_already_defined=1
        oldvalue=$(grep "^export ${varname}=" ${envfile} | cut -d= -f2-)
    else
        var_already_defined=0
        oldvalue=
    fi

    if [[ ${var_already_declared} -eq 1 ]]
    then
        if [[ ${oldvalue} = ${newvalue} ]]
        then
            echo "Environment: No change to existing value : ${varname} = ${oldvalue}"
        else
            if [[ ${mode} -eq 0  &&  ${var_already_defined} -eq 1 ]]
            then
                echo "Environment: Not updating existing value : ${varname} = ${oldvalue} --X--> ${newvalue}"
            else
                if [[ -z ${oldvalue} ]]
                then
                    echo "Environment: Setting value               : ${varname} => ${newvalue}"
                    varname=$varname newvalue=$newvalue perl -i -p -e 's/(\Q$ENV{"varname"}\E)=.*/${1}=$ENV{"newvalue"}/' ${envfile}
                else
                    echo "Environment: Overwriting value           : ${varname} : ${oldvalue} ---> ${newvalue}"
                    varname=$varname newvalue=$newvalue perl -i -p -e 's/(\Q$ENV{"varname"}\E)=.*/${1}=$ENV{"newvalue"}/' ${envfile}
                fi
            fi
        fi
    else
        echo "Environment: Adding value for ${varname}"
        echo "export ${varname}=${newvalue}" >> ${envfile}
    fi
}


# ==== HANDLE PARAMETERS PASSED BY DPM ====

#-- Parse DPM install options
for c in ${OPTIONS//,/ }        # $OPTIONS is a comma-delimited list, so split by ,
do
    case $c in
        InstallAsRoot             )  SUDO=sudo               ;;
        InstallLinuxService       )  INSTALL_LINUX_SERVICE=1 ;;
        SetVPEndpoints            )  SET_VP_ENDPOINTS=1      ;;
        SetWebServiceAuth         )  SET_WEB_SERVICE_AUTH=1  ;;
        SetWebServiceCertificate  )  SET_WEB_SERVICE_CERTIFICATE=1  ;;
    esac
done

for c in ${COMPONENTS//,/ }     # $COMPONENTS is a comma-delimited list, so split by ,
do
    case $c in
        WebService  )     INSTALL_WEB_SERVICE=1   ;;
        SelfService )     INSTALL_SELF_SERVICE=1  ;;
        DevTools    )     INSTALL_DEV_TOOLS=1     ;;
    esac
done

#-- Parameter validations
if [[ -z ${INSTALL_WEB_SERVICE}${INSTALL_SELF_SERVICE}${INSTALL_DEV_TOOLS} ]]
then
    echo "No components were selected for installation!"
    echo "Exiting!"
    exit 1
fi

#-- Amily root directory (e.g. /prjvl01/amily in original UTS environments)
if [[ -z ${AMILY_HOME} ]]
then
    echo "FATAL: AMILY_HOME was not set!"
    exit 1
fi

#-- If needing to 'sudo', then restart the whole script as sudo
if [[ -n ${SUDO} && $(id -u) != "0" ]]
then
    echo ">>> Installing as root"
    ${SUDO} $0 $@
    exit $?
    #-- the script terminates here --#
fi


#-- Set options for copying file from installation package
cp_options="-r -v -f"

echo

## ==== BEGIN INSTALLATION ====

#-- Create amily base directory, as root if necessary
mkdir -p ${AMILY_HOME}

#-- Copy the build_info file to AMILY_HOME
cp ${cp_options} ${BUILDINFO_FILE} ${AMILY_HOME}  || let error_count+=1

#-- Create env file, if it isn't already present from an earlier install
env_file=${AMILY_HOME}/${ENV_FILENAME}
env_file_template=$(pwd)/${ENV_TEMPLATE_FILENAME}

if [[ ! -f ${env_file} ]]
then
    echo "Environment: Creating new env file [${ENV_FILENAME}] from template [${ENV_TEMPLATE_FILENAME}]"
    cp ${env_file_template} ${env_file}  || let error_count+=1
fi

add_or_update_env_var 1 ${env_file} AMILY_HOME  ${AMILY_HOME}

#-- Flag sudo in the env.sh file
if [[ -n ${SUDO} ]]
then
    add_or_update_env_var 1 ${env_file} VP_INSTALLED_WITH_SUDO       TRUE
fi

#-- Record Python binaries path
if [[ -n ${PYTHON_BIN_PATH} ]]
then
    add_or_update_env_var 1 ${env_file} PYTHON_BIN_PATH ${PYTHON_BIN_PATH}
fi

#-- Install Amily web service
if [[ -n ${INSTALL_WEB_SERVICE} ]]
then
    echo "Installing Amily web service core layer"

    echo ".. installing Amily web service files"
    #-- Copy (maybe overwrite) file to the Amily runtime paths
    cp ${cp_options} ${SOURCE_DIR}/Amily_Prod ${AMILY_HOME}      || let error_count+=1
    cp ${cp_options} ${BUILDINFO_FILE} ${AMILY_HOME}/Amily_Prod  || let error_count+=1
    #-- Make scripts executable
    chmod 755 ${AMILY_HOME}/Amily_Prod/*sh
    echo

    #-- Create the Linux service start-stop script
    echo ".. creating Amily service start-stop script in the Amily Web Service home directory"

    cat > ${AMILY_HOME}/Amily_Prod/amily << EOF
#!/usr/bin/env bash
# This is the Linux service start/stop script for thr Amily web service
# When triggered using the 'service' command, the amily env is not loaded.
# So, we will load it by 'sudo'ing into the Amily user

sudo -u \$(id -un) -i ${AMILY_HOME}/Amily_Prod/amilyws.sh \${@}
EOF
    chmod 755 ${AMILY_HOME}/Amily_Prod/amily

    if [[ -n ${INSTALL_LINUX_SERVICE} ]]
    then
        echo ".. installing Amily service start-stop script in /etc/rc.d/init.d (via sudo)"

        # (Note, if ${SUDO} is TRUE, then we have already switched to and executing as user root)
        if [[ $(id -u) != "0" ]]
        then
            sudocmd=sudo
        else
            sudocmd=
        fi
        ${sudocmd} cp -v ${AMILY_HOME}/Amily_Prod/amily /etc/rc.d/init.d \
        && ${sudocmd} chmod 755 /etc/rc.d/init.d/amily \
        || {
               echo "*** WARNING: unable to install web service as a Linux service"
               let warning_count+=1
           }
    else
        echo ".. NOTE: to install amily as a linux service, run the commands:"
        echo "     cp ${AMILY_HOME}/Amily_Prod/amily /etc/rc.d/init.d"
        echo "     chmod 755 /etc/rc.d/init.d/amily"
    fi
    echo

    #-- Generate default logs dir full path
    if [[ -z ${AMILY_WS_LOGS_DIR} ]]
    then
        AMILY_WS_LOGS_DIR=${AMILY_HOME}/Amily_Prod/Logs
    fi

    #-- Update amily env file
    add_or_update_env_var 1 ${env_file} AMILY_WS_HOME       ${AMILY_HOME}/Amily_Prod
    add_or_update_env_var 1 ${env_file} AMILY_WS_LOGS_DIR   ${AMILY_WS_LOGS_DIR}

    if [[ -n ${AMILY_WS_HTTPS_PORT} ]]
    then
        add_or_update_env_var 1 ${env_file} AMILY_WS_HTTPS_LISTEN_PORT ${AMILY_WS_HTTPS_PORT}
    fi

    if [[ -n ${SET_WEB_SERVICE_AUTH} ]]
    then
        #-- Create the password file, if username and password creds were passed by DPM
        echo ".. creating web service password file"
        echo "   # ${PYTHON_BIN_PATH}/python ${AMILY_HOME}/Amily_Prod/${CREATE_WS_PASSWD_FILE_SCRIPT}"
        AMILY_WS_HOME=${AMILY_HOME}/Amily_Prod AMILY_WS_PASSWD_FILENAME=.htpasswd ${PYTHON_BIN_PATH}/python \
            ${AMILY_HOME}/Amily_Prod/${CREATE_WS_PASSWD_FILE_SCRIPT}
        add_or_update_env_var 1 ${env_file} AMILY_WS_PASSWD_FILENAME .htpasswd
        echo
    fi

    if [[ -n ${SET_WEB_SERVICE_CERTIFICATE} ]]
    then
        #-- Generate a self-signed certificate
        echo ".. generating a self-signed certificate"
        openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout ${AMILY_HOME}/Amily_Prod/SSL/selfsigned.key \
            -out ${AMILY_HOME}/Amily_Prod/SSL/selfsigned.crt -subj "/CN=${AMILY_WS_FRONTEND_HOST}"
        add_or_update_env_var 1 ${env_file} AMILY_WS_CERT_FILENAME selfsigned.crt
        add_or_update_env_var 1 ${env_file} AMILY_WS_CERT_PRIVATEKEY_FILENAME selfsigned.key
        echo
    fi

    echo
fi

if [[ -n ${INSTALL_SELF_SERVICE} ]]
then
    echo "Installing Amily Self Service files"
    cp ${cp_options} ${SOURCE_DIR}/Self_Service ${AMILY_HOME}      || let error_count+=1
    cp ${cp_options} ${BUILDINFO_FILE} ${AMILY_HOME}/Self_Service  || let error_count+=1

    #-- Generate default logs dir full path
    if [[ -z ${AMILY_SS_LOGS_DIR} ]]
    then
        AMILY_SS_LOGS_DIR=${AMILY_HOME}/Self_Service/Logs
    fi

    #-- Make scripts executable
    chmod 755 ${AMILY_HOME}/Self_Service/FS_Monitoring/*sh

    #-- Update amily env file
    add_or_update_env_var 1 ${env_file} AMILY_SS_HOME       ${AMILY_HOME}/Self_Service
    add_or_update_env_var 1 ${env_file} AMILY_SS_LOGS_DIR   ${AMILY_SS_LOGS_DIR}

    #-- Set VP endpoints in env file
    if [[ -n ${SET_VP_ENDPOINTS} ]]
    then
        add_or_update_env_var 1 ${env_file} AMILY_VP_NEXUS_URL   http://${VP_NEXUS_HOST}:${VP_NEXUS_PORT}/nexus
        add_or_update_env_var 1 ${env_file} AMILY_VP_NEXUS_USER  ${VP_NEXUS_USER}
        add_or_update_env_var 1 ${env_file} AMILY_VP_NEXUS_PASS  ${VP_NEXUS_PASS}
        add_or_update_env_var 1 ${env_file} AMILY_DPM_BASE_URL   https://${VP_DPM_HOST}:${VP_DPM_PORT}
        add_or_update_env_var 1 ${env_file} AMILY_DPM_AUTH_TOKEN ${VP_DPM_AUTH_TOKEN}
    fi

    echo
fi

if [[ -n ${INSTALL_DEV_TOOLS} ]]
then
    echo "Installing developer tools files"
    cp ${cp_options} ${SOURCE_DIR}/Amily_Test ${AMILY_HOME}  || let error_count+=1
    echo
fi

#-- Invoke the env file from .profile (Assumes sh/bash/ksh is being used)
if [[ ! -f ~/.profile ]]
then
    touch ~/.profile
    chmod 755 ~/.profile
fi

if ( ! grep -q "^. ${env_file}" ~/.profile )
then
    echo "Adding amily_env.sh to ~/.profile"
    echo >> ~/.profile
    echo "# Environment settings for Amily" >> ~/.profile
    echo ". ${env_file}" >> ~/.profile   || let error_count+=1
    echo
fi


#-- Finish up
if [[ ${error_count} -ne 0 ]]
then
    echo "!!! There were errors during deployment"
    exit 1
fi

case ${warning_count} in
    0)
        echo "--- Deployment completed."
        ;;
    1)
        echo "*** Deployment completed WITH 1 WARNING"
        ;;
    *)
        echo "*** Deployment completed WITH ${warning_count} WARNINGS"
        ;;
esac

exit 0
