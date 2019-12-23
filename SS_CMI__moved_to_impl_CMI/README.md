This directory contains the scripts and associated files required for Amily Self Service deployment in the CMI environment, covering the following functionality:

 - Invocation of model generation, and deployment to Dev and UAT environments
 - Invocation of threshold analysis script
 - Invocation of threshold modification script, and deployment to Dev and UAT environments

The above functionality is accessed by the user through the Terminal Server set up for this purpose.


INSTALLATION
============

There are the following components:

 - authorized_keys
      The contents of this file are copied to the file of the same name at utsadmin@cmilinutsaidev01:~/.ssh/authorized_keys
 - Remote_Execution/
      This directory is copied to all Amily Linux hosts to the path /prjvl01/amily/Self_Service/Remote_Execution
 - Terminal_Server/
      This directory is copied to the Terminal Server to the path "C:\Amily Self Service Model Deployment"


HOW IT WORKS
============

The self-service Python scripts for model generation, threshold analsysis, and threshold modification all exist under the Self_Service path of the Amily installation. However, the end-user does not have login access to the Linux servers in order to invoke them, or deploy the generated files.

Therefore we have written these scripts so the end-user can invoke the Linux-side scripts from the Terminal Server. They are based on several sequences of 'ssh' and 'scp' commands. For specifics of these sequences, see the comments header of each script.

Each 'ssh' and 'scp' command to an Linux environment is invoked from the Terminal Server using a specific SSH key for each function. On the Linux side, the 'authorized_keys' file is configured to execute a specific command for each given SSH key, thereby restricting the client to execution of a specific command, or access to a specific file/directory for SCP.


FILE PERMISSIONS
================

The directory containing the scripts deployed to the Terminal Server (C:\Amily Self Service Model Deployment) must have 'Modify' and 'Write' permissions for the group 'Users (CMIUTSTS01\Users)'. Other permissions (Read & Execute, List, Read) are inherited from the parent directory.

On the Linux servers, the files under 'Remote_Execution' are owned by user 'utsadmin' and have execute permissions.


FILE ASSOCIATIONS
=================

On the Terminal Server, the '.sh' files must be associated with the 'bash.exe' application from the Portable Git installation (under its 'bin' directory). This needs to be set on a per-user basis on the Terminal Server.


PREREQUISITES
=============

GitBash - The 'portable' mode of installation has been installed on the Terminal Server in order to run our scripts, which are written in Bash. It also supplies the SSH executables which are needed.

The scripts are invoked from the Terminal Server via ssh into the 'utsadmin' user. This user must be confugured for unrestricted (i.e. all commands) passwordless sudo.

