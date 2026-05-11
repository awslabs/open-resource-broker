# ORB Provider Deployment Documentation

This document describes how to configure the Open Resource Broker (ORB) as a provider in IBM Spectrum Symphony Host Factory.

## Installation of the Open Resource Broker

### Prerequisites
- Python 3.10+
- Git
- Virtual environment support

### Installation Steps
<details>
<summary>Development Install from Repository</summary>

Note: initial installation paths of IBM Symphony and Host Factory along with the exact ersions might be different.

```bash
#Navigate to the provider plugins directory
export EGO_TOP=/opt/ibm/spectrumcomputing
cd ${EGO_TOP}/hostfactory/1.2/providerplugins

#Clone the repository
mkdir -p orb
git clone https://github.com/awslabs/open-resource-broker.git ./orb
cd orb

#Follow ORB development installation steps from the documentation e.g.,
python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

orb --version

```

</details>



## Debug Logging

HostFactory logging splits into two layers: the HostFactory core daemon and the ORB provider plugin. Turn both on during first-time bring-up; turn them off once the deployment is stable.

<details>
<summary>More</summary>

### HostFactory core

The HostFactory daemon writes its own log independently of any provider plugin. To raise verbosity, edit the HostFactory configuration file:

```bash
vi /opt/ibm/spectrumcomputing/hostfactory/conf/hostfactoryconf.json

Set:

"HF_LOGLEVEL": "LOG_DEBUG"

```

### ORB provider plugin

Depending on the installation location and configuration

```bash
vi /opt/ibm/spectrumcomputing/hostfactory/work/config/config.json

  "logging": {
    "level": "DEBUG",
    "file_path": "logs/app.log",
    "console_enabled": false
  }

```

### Where the output goes

  - {HF_LOGDIR}/hostfactory.hostname.log — HostFactory core log.
  - ${HF_LOGDIR}/scripts.log - raw wire-format I/O: the JSON HostFactory sent in, and the JSON the plugin sent back, one block per call. Shows the exact communication between the plugin and the HhostFactory.
  - /opt/ibm/spectrumcomputing/hostfactory/1.2/providerplugins/orb/logs/orb.log — structured per-line JSON log for full ORB tracing.


### Other Settings

Set host_return_policy: immediate for debugging fo requestor plugin, then restart HostFactory. Default lazy returns hosts only at the 60-min billing boundary. Immediate returns any idle host within ~1 minute. This provides fast feedback during debugging and testings. Revert to lazy before production.

```bash
vim ${EGO_TOP}/hostfactory/conf/requestors/symAinst/symAinstreq_config.json

"host_return_policy": "immediate"

```


</details>


## Configuration of Host Factory to use ORB as a new provider plugin

### Step 1: Register ORB provider with HostFactory

Edit the provider configuration file:
```bash
vim ${HF_TOP}/hostfactory/conf/providers/hostProviders.json
```

Add the ORB provider configuration, (optionally) disable other providers:
```json
{
  "version": 2,
  "providers": [
    {
			"name":	"orb",
			"enabled":	1,
			"plugin":	"orb",
			"confPath":	"${HF_CONFDIR}/providers/orb/",
			"workPath":	"${HF_WORKDIR}/providers/orb/",
			"logPath":	"${HF_LOGDIR}/"
		},
    ...
  ]
}
```

## Step 2: Register ORB provider plugin with HostFactory

Edit the provider plugins configuration:
```bash
vim ${HF_TOP}/hostfactory/conf/providerplugins/hostProviderPlugins.json
```

Add the ORB plugin configuration and disable other plugins:
```json
{
    "version": 2,
    "providerplugins":[
        {
            "name": "orb",
            "enabled": 1,
            "scriptPath": "${HF_TOP}/${HF_VERSION}/providerplugins/orb/scripts/"
        },
        ...
    ]
}
```



### Step 3: Create provider directory

Navigate to the providers folder and create a folder for the new provider. HostFactory will check for the presence of this path, however, actual configuration of ORB will not be kept here.
```bash
# create directory
mkdir vim ${HF_TOP}/hostfactory/conf/providers/orb

```


## Step 4: Configure Requestor

Configure the requestor to recognize the new provider:
```bash
vim ${HF_TOP}/hostfactory/conf/requestors/hostRequestors.json
```

Update the requestor configuration:
```json
{
    "version": 2,
    "requestors": [
        {
            "name": "symAinst",
            "enabled": 1,
            "plugin": "symA",
            "confPath": "${HF_CONFDIR}/requestors/symAinst/",
            "workPath": "${HF_WORKDIR}/requestors/symAinst/",
            "logPath": "${HF_LOGDIR}/",
            "providers": ["orb"],         # <-----
            "requestMode": "POLL"
        },
        {
            "name": "admin",
            "enabled": 1,
            "providers": ["orb"],         # <-----
            "requestMode": "REST_MANUAL"
        }
    ]
}
```

### Set HostFactory Environmental Variables for ORB

HostFactory does not pick up variables from .bashrc, instead it has its own environmental files. One way to set it is by editing the following file.

```bash

vim ${HF_TOP}/hostfactory/conf/profile.hf

# runs ORB without system wide installation
export USE_LOCAL_DEV=true

# records complete scripts I/O between HostFactory and ORB
export LOG_SCRIPTS=true

```




## Configure ORB

This step will set defaults for ORB in current AWS account. It will also move scripts directory under orb/ path to match configuration above.
```bash
orb init
orb templates generate
```

export USE_LOCAL_DEV="true"         # Set true for this type of deployment





## Directory Structure

After configuration, your directory structure should look like:


hostfactory/work/providers/aws_orb_provider/dataopt/ibm/spectrumcomputing/hostfactory/work/providers/aws_orb_provider/data/
```
hostfactory
├── conf/
│   ├── providers/
│   │   ├── awsinst/                    # Original AWS provider (disabled)
│   │   ├── aws_orb_provider/          # New ORB provider
│   │   │   ├── <...>                   # Currently no config files here!
│   │   └── hostProviders.json          # Provider registry (update)
│   ├── providerplugins/
│   │   └── hostProviderPlugins.json    # Plugin registry (update)
│   └── requestors/
│       └── hostRequestors.json         # Requestor configuration (update)
├── work/
│   └── config/                         # config.json, default-config.json, awsprov_templates.json
│   └── logs/
│       └── app.log                     # ORB Plugin Logs
│   └── providers/
│       └── aws_orb_provider/
│           └── data/
├               ├──request_database.json. # Request/machine data
├── log/
│   ├── hostfactory.log                 # Host Factory logs
│   └── scripts.log                     # Logs from Host Factory scripts invocation for debug.
│   └── symAinst.log                    # Requestors logs
└── 1.2/
    └── providerplugins/
        └── orb/
            ├── .venv/
            ├── src/                    # ORB source code
            └── scripts/                # Provider scripts
                ├── getAvailableTemplates.sh
                ├── requestMachines.sh
                ├── getRequestStatus.sh
                └── requestReturnMachines.sh
                └── invoke_provider.sh         # Edit this file


```


### Log Locations

Check these log files for troubleshooting:
- **Host Factory logs:** `/opt/ibm/spectrumcomputing/hostfactory/log/hostfactory.log`
- **ORB application logs:** `/opt/ibm/spectrumcomputing/hostfactory/log/app.log`
- **Provider work directory:** `/opt/ibm/spectrumcomputing/hostfactory/work/providers/aws_orb_provider/`

## Execution

To apply any configuration changes you need to restart HostFactory

```bash
egosh service stop HostFactory
sleep 2
egosh service start HostFactory
```

To have a clean run, you can remove all the previous state associated with HF and requestor plugin (adjust to your paths):

```bash
rm /opt/ibm/spectrumcomputing/hostfactory/work/*.json -f
rm /opt/ibm/spectrumcomputing/hostfactory/log/* -f
rm /opt/ibm/spectrumcomputing/hostfactory/work/logs/app.log -f
rm /opt/ibm/spectrumcomputing/hostfactory/work/requestors/symAinst/* -f
rm /opt/ibm/spectrumcomputing/hostfactory/db/hf.db -f
rm /opt/ibm/spectrumcomputing/hostfactory/1.2/providerplugins/orb/awscpinst/data/*.json -f
```

Note: symAinst-requestor.log is visible only if plugin successfully started and returned list of available templates.

