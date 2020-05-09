#!/usr/bin/python3

import os

###########################################################
# Note: Requires Python 3.5+                              ##
# Version: 1.0                                            ##
# Created for GOCD Server                                 ##
###########################################################
import hvac
import yaml

# function to read Vault role and secret id from docker secrets
def readVaultCreds(filename):
    if os.path.exists(filename):  # check if file exists or raise exception
        vaultCredsFile = filename
        vaultConfigFileOpen = open(vaultCredsFile, "r")
        vaultConfigFileRead = yaml.load(vaultConfigFileOpen, Loader=yaml.FullLoader)
        vaultConfigFileOpen.close()
        vaultRole = vaultConfigFileRead['role-id']  # reading role id from secret
        vaultSecret = vaultConfigFileRead['secret-id']  # reading secret id from secret
    else:
        raise FileNotFoundError("{file} is empty or not found".format(file=vaultCredsFile))
    return vaultRole, vaultSecret


def getVaultSecrets(mountpoint,path,key):
    print("Retreiving {key} from vault".format(key=key))
    secret = client.secrets.kv.v2.read_secret_version(
        mount_point=mountpoint,
        path=path
    )
    return secret['data']['data'][key]


# Load Vault creds from docker secrets
# Add all your environment based file paths
#os.environ['GO_STAGE_NAME'] = "dev"

if os.getenv('GO_STAGE_NAME') in "dev":
    #    vaultRoleId, vaultSecretId = readVaultCreds('/run/secrets/vault-dev')
    vaultRoleId, vaultSecretId = readVaultCreds("/run/secrets/vault-dev")

elif os.getenv('GO_STAGE_NAME') in "prod":
    vaultRoleId, vaultSecretId = readVaultCreds('/run/secrets/vault-prod')
# raise exception if none of the above condition matches any file
else:
    raise EnvironmentError('GO_STAGE_NAME Environment is not loaded')

# Vault client setup and authentication
vaultAddress = os.getenv('VAULT_URL')
#vaultAddress = 'https://vault.example.local'
client = hvac.Client(url=vaultAddress)
try:
    client.auth_approle(role_id=vaultRoleId, secret_id=vaultSecretId, mount_point='approle')
    print("Success: Connected to Vault")
except Exception as Error:
    print("Error: Connecting to Vault")
    exit(1)
    # raise ConnectionError('Not Connected to vault')

# Load list of variables to retrieved from vault using pipeline.yml
pipelineFile = "pipeline.yml"
pipelineFileOpen = open(pipelineFile, "r")
pipelineConfig = yaml.load(pipelineFileOpen, Loader=yaml.FullLoader)
pipelineFileOpen.close()

# Check if vault retrival is enabled in pipeline config
envAddedList = []
tempFile = open('./tempvaultenv','w+')
if pipelineConfig['vault']['enabled'] == True:
    secretKv = 'secrets/'  # change secret kv engine path
    secretEnv = os.getenv('GO_STAGE_NAME')
    secretFolder = pipelineConfig['vault']['name']
    secretPath = 'apps/' + "/" + secretEnv + '/' + secretFolder  # change secret kv engine sub path [here its apps]
    for key in pipelineConfig['vault'][os.getenv('GO_STAGE_NAME')]:
        # Set env from vault
        os.environ[key] = getVaultSecrets(secretKv,secretPath,key)
        tempFile.write('export ' + key + '=' + os.getenv[key] )
        envAddedList.append(key)
    tempFile.close() 

#Print ENV
print ("{:<40} {:<40}".format('ENV_NAME','Hashed_Value'))
for env in envAddedList:
    print("{:<40} {:<40}".format(env,hash(os.getenv(env))))
