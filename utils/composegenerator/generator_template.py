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
tempateComposeFile = open(os.path.join(sys.path[0],"docker-compose-template.yml"), "r+", encoding='utf-8')
finalComposeFiledata = yaml.load(srcComposeFile, Loader=yaml.FullLoader)
tempateComposeFiledata = yaml.load(tempateComposeFile, Loader=yaml.FullLoader)
srcComposeFile.close()

for service in finalComposeFiledata["services"].keys():
    if service == args.servicename :
    
        # changing version
        finalComposeFiledata["version"] = tempateComposeFiledata["version"]
        # Adding Networks
        finalComposeFiledata["networks"] = tempateComposeFiledata["networks"]

        # Adding Env file to Service
        finalComposeFiledata["services"][service]["env_file"] = tempateComposeFiledata["services"]["template"]["env_file"]
        
        # Adding network to service
        finalComposeFiledata["services"][service]["networks"] = tempateComposeFiledata["services"]["template"]["networks"]

        
        # Adding Deploy Section settings
        finalComposeFiledata["services"][service]["deploy"] = tempateComposeFiledata["services"]["template"]["deploy"]

        

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
output_file = open(os.path.join(sys.path[0],"docker-compose-env.yml"), "w+", encoding='utf-8')
yaml.safe_dump(finalComposeFiledata, output_file, default_flow_style=False)