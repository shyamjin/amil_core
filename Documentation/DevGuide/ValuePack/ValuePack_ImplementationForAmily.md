# Value Pack Implementation for Amily

## Code Layers

For Amily, we created 2 'tools', effectively as code layers. These are named:
- atomIQ_Ticketing _(core)_
- atomIQ_Ticketing_Impl _(implementation)_

(The Git repos have the same name, in all lower case).

The idea is that the Amily 'core' team will maintain the core layer, "atomiq_ticketing", while the Impl layer will be
maintained by Amdocs customer account teams, to customize to their needs.

The Impl layer contains code and configuration appropriate for each customer's needs. This includes:
- Customer-specific Atoms
- Customer-specific parsing configuration
- A list of account names to be handled by Amily

and possibly also environment-specific configurations, such as:
- password files
- SSL certificates and keys
- Value Pack endpoint information

However, it's not generally recommended to put environment-specific data in a source code repository, but it does 
make it easier for a full deployment to be done from the DPM GUI. If necessary, the installation script in Impl can
be adjusted to detect which environment file to deploy from the repo, e.g. to deploy the correct SSL certificate 
based on the hostname of the runtime environment.

## Mode of Installation

To install Amily, high-level process is:
- Manually install Anaconda plus additional library & data dependencies required by Amily.
- VP end-user deploys the core ("atomiq_ticketing")
- VP end-user deploys the impl ("atomiq_ticketing_impl")
- (possibly) Manual post-installation steps from the Linux command line.

## Propagation Through VP Environments

We have two code layers (core + impl), and three layers of VP environments (master, account, customer network).

Remember, each environment contains the following components:

    [G][N][D][R]

whereby:
- G = GitLab (tool source code)
- N = Nexus  (built artifacts / .zip files)
- D = DPM
- R = Runtime environment (where we deploy the tools from the zip files)

Note: the runtime environment is not supplied as part of VP. It needs to be acquired separately.

The above picture actually depicts the places where Amily code is, in any form (e.g. source, compiled, etc), in each 
stage of the CI/CD path. [G]=source code in Git; [N]=the zip file in Nexus; [D]=the deployment configuration of Amily
in DPM; [R]=Amily installed in runtime. In reality, both core & impl layers are hosted in the same GitLab, Jenkins, 
DPM, and runtime instance -- I want here to highlight _where_ the Amily code is residing in the VP components.
    
Amily in the master environment looks like this:

````
Master Environment
==================

Core     [G][N][D][R]

Impl     [G][N][D][R]
````

(Again: There's only one Git/Nexus/DPM in the master env; the diagram shows where the core and impl code exists).
Both core and Impl exist in the same VP and runtime environments. 

The Amily core team maintains both the Core and Impl layers at the VP master level, and can deploy to a runtime 
environment for development testing.

When the tool is ready for release, the VP core + impl instance gets cloned to one or more independent account 
instances. However, in the core layer, only Nexus artifacts and DPM config are copied. 

````
Account Environment
===================

Core        [N][D][R]

Impl     [G][N][D][R]
````

In the above, the account developers do not have the source code for core. They have the core artifacts in Nexus and 
can deploy core to runtime. However, they have full source code access to the Impl layer, can build *and* deploy the 
Impl layer.  

Finally, when the account developers are ready to deploy to production, the account environment is cloned, without 
the Impl source code.

````
Customer Network
================

Core        [N][D][R]

Impl        [N][D][R]
````


In fact, you will likely have multiple runtime environments on the customer network:
````
Customer Network
================

Core        [N][D][R-dev][R-UAT][R-Prod x 2]

Impl        [N][D][R-dev][R-UAT][R-Prod x 2]
````

## Deployment Unit (DU)

The Impl layer contains customer-specific code and configuration. However, files that are generated in the runtime 
environment (thresholds and model pickles) are not able to propagate upwards to the VP account environment. (Anyway, 
such data should be stored Nexus and not source control). 

The solution to this is **Deployment Units**.

A "DU" is another .zip file that can be versioned, stored in Nexus, and deployed via DPM, in the same way as the core
and Impl artifacts are.

For example, when the Amily Self Service generates a model (let's say, NLP Preprocessor pickle, plus the Classification 
pickle), we bundle those files into a .zip file, upload to Nexus, and inform DPM of the new .zip file and its 
'version' number that we give it. This mimics the build process executed by Jenkins for the Amily source code. The 
end-user can later deploy any DU that was generated, to any runtime environment. The exact same process applies to 
new threshold files that may be generated through threshold analysis executed locally in the customer network.

````
Customer Network
================

Core        [N][D][R-dev][R-UAT][R-Prod x 2]

Impl        [N][D][R-dev][R-UAT][R-Prod x 2]

DU          [N][D][R-dev][R-UAT][R-Prod x 2]
````

Typically, you generate a DU inside a self-service runtime environment, and push it to Nexus & inform DPM:
````
Customer Network
================

DU          [N][D][R-dev][R-UAT][R-Prod x 2][R-Prod-SS]
             ^  ^                                |
             |  :                                v
              \ :                               /
               -----<-----<-----<-----<-----<---
````
Then you ask DPM to deploy it to UAT for testing:
````
Customer Network
================

DU          [N][D][R-dev][R-UAT][R-Prod x 2][R-Prod-SS]
             |               ^
             v               |
              \             /
               ---->----->--
````
When satified, you ask DPM to deploy the same DU to production:
````
Customer Network
================

DU          [N][D][R-dev][R-UAT][R-Prod x 2][R-Prod-SS]
             |                      ^
             v                      |
              \                    /
               ---->----->----->---
````
You can also instruct DPM to deploy an earlier version of the DU, thereby providing a rollback mechanism.