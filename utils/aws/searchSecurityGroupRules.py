#!/usr/bin/python
import json
import argparse
import boto3


#Argument parser
parser = argparse.ArgumentParser(description='Search rules in SG matching the IPaddress')
parser.add_argument('--type', metavar='In/Out', type=str, nargs=1,dest='type',
                    help='Inboud or Outbound')
parser.add_argument('--IP', metavar='xx.xx.xx.xx', type=str, nargs='+',dest='ipaddress',
                    help='enter the ip to search')
args = parser.parse_args()


ec2 = boto3.client('ec2')
response = ec2.describe_security_groups()
response1 = json.dumps(response) # remove unicode strings
data = json.loads(response1)

if args.type[0] in ['inbound','Inbound']:
    for group in data["SecurityGroups"]:
        for Ingress in group["IpPermissions"]:
           for ip in Ingress["IpRanges"]:
              if ip["CidrIp"] in args.ipaddress:
                  try:
                      print "{},{},{},{}".format(group["GroupName"], group["GroupId"], ip["CidrIp"], Ingress["ToPort"])
                  except KeyError as e:
                      print "{},{},{},{}".format(group["GroupName"], group["GroupId"],ip["CidrIp"],  Ingress["IpProtocol"])


elif args.type[0] in ['Outbound','outbound']:
    for group in data["SecurityGroups"]:
        for Egress in group["IpPermissionsEgress"]:
           for ip in Egress["IpRanges"]:
              if ip["CidrIp"] in args.ipaddress:
                  try:
                      print "{},{},{},{}".format(group["GroupName"], group["GroupId"], ip["CidrIp"], Egress["ToPort"])
                  except KeyError as e:
                      print "{},{},{},{}".format(group["GroupName"], group["GroupId"],ip["CidrIp"],  Egress["IpProtocol"])

else:
    print  "Invalid Input for --type"
