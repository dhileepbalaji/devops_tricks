from __future__ import print_function
#!/usr/bin/python
###############################################################
#Version 1.0
#Deploy Docker Swarm Stack based on swarmconfig.yml
#This script designed for GOCD CI/CD tool
###############################################################
import yaml
import os
import subprocess
import sys
#import tabulate

#Read Pipeline Settings from yaml file
swarmStackDeployConfig = "pipeline.yml"
yamlConfigOpen = open(swarmStackDeployConfig, "r+")
yamlConfig = yaml.load(yamlConfigOpen, Loader=yaml.FullLoader)
yamlConfigOpen.close()


#os.environ['GO_STAGE_NAME'] = "dev"

#Function to check handle yaml empty values and throw errors
ENV_LIST = []
def configemptyvalue(env,configkey,errormessage):
    if configkey is not None:
        os.environ[env] = str(configkey)
        ENV_LIST.append(env)
    else:
        print(errormessage)
        exit(1)


#Set ENV: Docker StackName from config
configemptyvalue('STACKNAME',yamlConfig["stackname"],
                 "Error: stackname is empty in config ")
#Set ENV: Docker envfolder from config
configemptyvalue('ENVFOLDER',yamlConfig["env_folder"],
                 "Error: env_folder is empty in config ")
#Set ENV: Docker restart_policy from config
configemptyvalue('SERVICE_RESTART_CONDITION',yamlConfig["restart_policy"],
                 "Error: restart_policy is empty in config ")
#Set ENV: traefik_application_port from config
configemptyvalue('TRAEFIK_PORT',yamlConfig["traefik_application_port"],
                 "Error: traefik_application_port is empty in config ")
#Set ENV: traefik_https_enable from config
configemptyvalue('TRAEFIK_SSL_ENABLE',yamlConfig["traefik_https_enable"],
                 "Error: traefik_https_enable is empty in config ")
#Set ENV: traefik_ssl_provider from config
configemptyvalue('TRAEFIK_SSL_CERTRESOLVER',yamlConfig["traefik_ssl_provider"],
                 "Error: traefik_ssl_provider is empty in config ")
#Set ENV: docker replicas from config
if yamlConfig["replicas"] is not None and os.getenv('GO_STAGE_NAME') in "dev":
    configemptyvalue('NUMBER_REPLICAS', yamlConfig["replicas"][os.getenv('GO_STAGE_NAME')],
                     "Error: replicas dev is empty in config ")
elif yamlConfig["replicas"] is not None and os.getenv('GO_STAGE_NAME') in "qa":
    configemptyvalue('NUMBER_REPLICAS', yamlConfig["replicas"][os.getenv('GO_STAGE_NAME')],
                     "Error: replicas qa is empty in config ")
elif yamlConfig["replicas"] is not None and os.getenv('GO_STAGE_NAME') in "uat":
    configemptyvalue('NUMBER_REPLICAS', yamlConfig["replicas"][os.getenv('GO_STAGE_NAME')],
                     "Error: replicas uat is empty in config ")
elif yamlConfig["replicas"] is not None and os.getenv('GO_STAGE_NAME') in "prod":
    configemptyvalue('NUMBER_REPLICAS', yamlConfig["replicas"][os.getenv('GO_STAGE_NAME')],
                     "Error: replicas prod is empty in config ")
else:
    print("Error: Replicas is not set in config file")


#Print ENV
print ("{:<40} {:<40}".format('ENV_NAME','VALUE'))
for env in ENV_LIST:
    print("{:<40} {:<40}".format(env,os.getenv(env)))

#Deploy Stack
dockerDeployStack = "docker stack deploy -c " + os.getenv('COMPOSE_FILE_NAME') + \
                    os.getenv('STACKNAME') + "_" + "${GO_STAGE_NAME}"
if (sys.version_info < (3, 0)):
    # Python 2 code in this block
    import commands
    dockerDeployStackProcess = commands.getoutput(dockerDeployStack)
else:
    dockerDeployStackProcess = subprocess.getoutput(dockerDeployStack)
    
    
print(dockerDeployStack)

