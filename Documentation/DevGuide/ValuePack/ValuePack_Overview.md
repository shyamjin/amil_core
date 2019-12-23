# Value Pack Overview

## What is Value Pack

"Value Pack" is a CI / CD solution tailored for AIO tools.

The goal is that all tools onboarded to the Value Pack solution will be deployable to any environments by the end 
user purely from the DPM GUI. Direct command line access to the target runtime server should never be needed for 
deployment.

Value Pack has the following components:
- GitLab server, hosting git repos with AIO tool source code.
- Jenkins build server
- Nexus repository server
- DPM

Note, the Value pack does not include a runtime environment. This (these) must be provided separately.

## Glossary

- **CI = Continuous Integration**. When a developer commits a change to the source code repo (Git), then the build 
process will be triggered automatically. For Value Pack, the build process can be defined by the developer, but at a 
minimum it creates a zip file 'package' which will later be pushed to the runtime environment and used to perform the
installation.

- **CD = Continuous Delivery**. CD takes CI one step further, and also deploys the built package into a runtime 
environment. Value Pack doesn't actually do 'continuous' deployment (yet?), but makes it easy to deploy a package 
right from the DPM GUI.

- **Jenkins**. The de-facto industry-standard CI execution platform. Jenkins is a Java-based application, providing a 
framework to make automation of builds easy to do. It provides: orchestration of build steps, dependency management, 
source control integration, a fully-featured front-end GUI for configuration, execution, and monitoring, with 
end-user access control. Jenkins became popular largely due to its extensibility which makes it possible to customize
it for your needs. There is a large, public repository of user-contibuted add-ons.

- **Nexus**. An 'artifact' repository. It's like version control for stuff that was already build, with an HTTP API 
allowing artifacts to be addressed by 'group', 'artifact name', 'version', and additional attributes. Artifact 
repositories like Nexus follow the addressing conventions introduced by the build tool 'maven', but the conventions 
remain useful in general for deployable artifacts.

- **DPM = Deployment Manager**. This is the central orchestrator of the Value Pack solution. It tracks builds and 
deployments, and provides the front-end GUI for managing deployment activities and status.

- **eDPM = enterprise DPM**. This is a lightweight version of the DPM with some functionality removed.

- **VP = Value Pack**

## Value Pack Process

Here's the general development process, in the order it happens:

- Write code (on your PC, in an IDE like PyCharm)
- Commit to your local Git repo (on your PC)
- Push to GitLab
- Jenkins executes the build
  - Clone the repo from GitLab into the Jenkins local 'workspace'.
  - Execute 'build.sh' in the base directory of the repo. Creates a .zip file.
  - Upload the .zip file to Nexus.
  - Update DPM with the details of the build and location of .zip file in Nexus.
- User logs into DPM GUI and triggers deployment of tool to runtime environment
  - DPM GUI prompts user for configuration parameters.
  - DPM downloads .zip file from Nexus and pushes it to runtime environment, to a temporary staging directory.
  - DPM unzips the file in-place.
  - DPM executes 'install.sh' (that came from inside the .zip file). User-supplied configuration parameters are passed
   to the install.sh as shell environment variables.

## Value Pack Environments

**Master** - This is the top level environment, where the 'core' AIO developers submit their code to the 
git repos. AIO tools will be built here and stored in the Master's Nexus repo. Tools can also be deployed from the 
Master's DPM into a runtime environment.

**Account** -  This is a clone of the VP master environment, containing only the AIO tools that are required / 
requested for a given account. The VP account environment can be resynched from the master to propagate the latest code 
down to the account environment.

**Customer Network** - A lightweight clone of the account environment. Contains only: Nexus, eDPM. This reduced VP 
environment is designed to installation into non-Amdocs networks where we wish to only expose deployable artifacts 
and the deployment functionality. The VP customer network environment can be resynched from the account environment 
to propagate the latest built artifacts down to the customer network.

Note that VP currently propagates only downwards. There is no mechanism to propagate artifacts generated in lower 
levels back to higher levels.