#!/usr/bin/python
import yaml
import argparse
import os,sys
# Create the parser
arg_parser = argparse.ArgumentParser(description='Generate Compose file')
# Add the arguments
arg_parser.add_argument('--servicename', required=True, metavar='servicename', type=str,
                        help='enter the service name used in compose file to add customization')
arg_parser.add_argument('--composefileaname', required=False, metavar='composefileaname', type=str,
                        default="docker-compose-env.yml",
                        help='enter the src composefileaname to add customization')

# Execute the parse_args() method
args = arg_parser.parse_args()

srcComposeFile = open(os.path.join(sys.path[0],args.composefileaname), "r+", encoding='utf-8')
finalComposeFiledata = yaml.load(srcComposeFile, Loader=yaml.FullLoader)
srcComposeFile.close()

for service in finalComposeFiledata["services"].keys():
    if service == args.servicename :
    
        # changing version
        finalComposeFiledata["version"] = "3.7"
        # Adding Networks
        finalComposeFiledata["networks"] = {}
        finalComposeFiledata["networks"]["default"] = None
        finalComposeFiledata["networks"]["traefik"] = {}
        finalComposeFiledata["networks"]["traefik"]["external"] = True
        finalComposeFiledata["networks"]["traefik"]["name"] = "${TRAEFIK_NETWORK}"
        
        # Adding Env file to Service
        finalComposeFiledata["services"][service]["env_file"] = "env_vars/${GO_STAGE_NAME}.env"
        
        # Adding network to service
        finalComposeFiledata["services"][service]["networks"] = []
        finalComposeFiledata["services"][service]["networks"].append("default")
        finalComposeFiledata["services"][service]["networks"].append("traefik")
        
        # Adding Deploy Section settings
        finalComposeFiledata["services"][service]["deploy"] = {}
        finalComposeFiledata["services"][service]["deploy"]["replicas"] = "${NUMBER_REPLICAS}"
        finalComposeFiledata["services"][service]["deploy"]["update_config"] = {}
        finalComposeFiledata["services"][service]["deploy"]["update_config"]["parallelism"] = 1
        finalComposeFiledata["services"][service]["deploy"]["update_config"]["delay"] = "30s"
        finalComposeFiledata["services"][service]["deploy"]["restart_policy"] = {}
        finalComposeFiledata["services"][service]["deploy"]["restart_policy"][
            "condition"] = "${SERVICE_RESTART_CONDITION}"
        finalComposeFiledata["services"][service]["deploy"]["restart_policy"]["delay"] = "10s"
        
        # Adding labels to Deploy Section
        traefikLabels = ["traefik.frontend.rule=${TRAEFIK_FRONTEND_HOST}", "traefik.enable=true",
                         "traefik.port=${TRAEFIK_PORT}", "traefik.docker.network=${TRAEFIK_NETWORK}",
                         "traefik.tags=${TRAEFIK_TAGS}"]

        rateLimitLabels = ["traefik.frontend.rateLimit.rateSet.test.period=1s",
                           "traefik.frontend.rateLimit.rateSet.test.burst=30",
                           "traefik.frontend.rateLimit.rateSet.test.average=10",
                           "traefik.frontend.rateLimit.extractorFunc=client.ip"]
        
        finalComposeFiledata["services"][service]["deploy"]["labels"] = []
        finalComposeFiledata["services"][service]["deploy"]["labels"] = traefikLabels + rateLimitLabels
        

    else:
        # Adding network to service
        finalComposeFiledata["services"][service]["networks"] = []
        finalComposeFiledata["services"][service]["networks"].append("default")

# handling none type values
yaml.SafeDumper.add_representer(
    type(None),
    lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:null', '')
)

# Output_file
output_file = open(os.path.join(sys.path[0],"docker-compose-env1.yml"), "w+", encoding='utf-8')
yaml.safe_dump(finalComposeFiledata, output_file, default_flow_style=False)
