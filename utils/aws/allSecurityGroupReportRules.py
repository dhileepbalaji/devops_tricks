
######################################################################################################################
# Purpose:      Generate rule report of all the security groups                                                      #
# Usage:        ./allSecurityGroupReportRules.py  > account-date                                                     #
# Author:       Dhileepkumar.p                                                                                       #
# Doc. Ref:     http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_security_groups#
######################################################################################################################
from __future__ import print_function
from sys import argv
import json
import boto3

#See if any argument was passed. First argument is the script name, skip that one (-1)
arguments = len(argv) - 1

#Explicitly declaring variables here grants them global scope
sgs = ""
cidr_block = ""
ip_protpcol = ""
from_port = ""
to_port = ""
port_range = ""
from_source = ""

print("%s,%s,%s,%s,%s,%s" % ("Group-Name","Group-ID","In/Out","Protocol","Port","Source/Destination"))

for region in ["us-east-1","us-west-1", "us-west-2"]:
	ec2=boto3.client('ec2', region )

	if arguments == 0:
		sgs = ec2.describe_security_groups()["SecurityGroups"]
	else:
		#Filter on passed SG ID
			sgs = ec2.describe_security_groups(
				Filters=[
		        	{
		            	'Name': 'group-id',
		            	'Values': [argv[1]]
		        	}
		    	]
			)["SecurityGroups"]

	for sg in sgs:
		group_name = sg['GroupName']
		group_id = sg['GroupId']
		print("%s,%s" % (group_name,group_id))
		# InBound permissions ##########################################
		inbound = sg['IpPermissions']
		print("%s,%s,%s" % ("","","Inbound"))
		for rule in inbound:
			if rule['IpProtocol'] == "-1":
				traffic_type="All Trafic"
				ip_protpcol="All"
				to_port="All"
			else:
				ip_protpcol = rule['IpProtocol']
				from_port=rule['FromPort']
				to_port=rule['ToPort']
				if from_port == to_port:
					port_range = from_port
				else:
					port_range = str(from_port) + ' - ' + str(to_port)
				#If ICMP, report "N/A" for port #
				if to_port == -1:
					to_port = "N/A"

			#Is source/target an IP v4?
			if len(rule['IpRanges']) > 0:
				for ip_range in rule['IpRanges']:
					cidr_block = ip_range['CidrIp']
					print("%s,%s,%s,%s,%s,%s" % ("", "", "", ip_protpcol, port_range, cidr_block))

			#Is source/target an IP v6?
			if len(rule['Ipv6Ranges']) > 0:
				for ip_range in rule['Ipv6Ranges']:
					cidr_block = ip_range['CidrIpv6']
					print("%s,%s,%s,%s,%s,%s" % ("", "", "", ip_protpcol, port_range, cidr_block))

			#Is source/target a security group?
			if len(rule['UserIdGroupPairs']) > 0:
				for source in rule['UserIdGroupPairs']:
					from_source = source['GroupId']
					print("%s,%s,%s,%s,%s,%s" % ("", "", "", ip_protpcol, port_range, from_source))

		# OutBound permissions ##########################################
		outbound = sg['IpPermissionsEgress']
		print("%s,%s,%s" % ("","","Outbound"))
		for rule in outbound:
			if rule['IpProtocol'] == "-1":
				traffic_type="All Trafic"
				ip_protpcol="All"
				to_port="All"
			else:
				ip_protpcol = rule['IpProtocol']
				from_port=rule['FromPort']
				to_port=rule['ToPort']
				if from_port == to_port:
					port_range = from_port
				else:
					port_range = str(from_port) + ' - ' + str(to_port)
				#If ICMP, report "N/A" for port #
				if to_port == -1:
					to_port = "N/A"

			#Is source/target an IP v4?
			if len(rule['IpRanges']) > 0:
				for ip_range in rule['IpRanges']:
					cidr_block = ip_range['CidrIp']
					print("%s,%s,%s,%s,%s,%s" % ("", "", "", ip_protpcol, port_range, cidr_block))

			#Is source/target an IP v6?
			if len(rule['Ipv6Ranges']) > 0:
				for ip_range in rule['Ipv6Ranges']:
					cidr_block = ip_range['CidrIpv6']
					print("%s,%s,%s,%s,%s,%s" % ("", "", "", ip_protpcol, port_range, cidr_block))

			#Is source/target a security group?
			if len(rule['UserIdGroupPairs']) > 0:
				for source in rule['UserIdGroupPairs']:
					from_source = source['GroupId']
					print("%s,%s,%s,%s,%s,%s" % ("", "", "", ip_protpcol, port_range, from_source))
