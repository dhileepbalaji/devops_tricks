#!/usr/bin/python3

###########################################################
#Note: Requires Python 3.5+                              ##
#Version: 1.0                                            ##
#To filter manager serice add label manager.service=true ##
###########################################################
from loguru import logger
import sys
import os
import subprocess
import json
import datetime

#Log file PATH BASED ON OS
#OS DETECTION
if "win" in sys.platform :
    filename = "C:/logs/swarmrebalance.log"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
elif "linux" in sys.platform:
    filename = "/var/logs/swarmrebalance.log"
    os.makedirs(os.path.dirname(filename), exist_ok=True)

#logger config
logger.add(filename,level='INFO', format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
           serialize=False,backtrace=False,diagnose=False,enqueue=False,
           rotation="1 week",retention="90 days", compression="zip")

logger.info("Script Execution Started")
#MAIN VARIBLES
logger.info("Loading Main Variables")
rebalanceService = False
newNodesJoined = []
dockerNodeList = "docker node ls --filter role=worker -q"
dockerServiceList = 'docker service ls -q | grep -v -E $(docker service ls -q --filter label=manager.service ' \
                    '| paste -sd "|" -)'
dockerRebalanceService = "docker service update  --detach=false --force "

logger.info("Running dockerNodeListProcess,dockerServiceListProcess")
dockerNodeListProcess = subprocess.getoutput(dockerNodeList)
dockerServiceListProcess = subprocess.getoutput(dockerServiceList)


for node in dockerNodeListProcess.splitlines():
    logger.info("Running dockerNodeInspect,dockerNodeInspectJson in " + node)
    dockerNodeInspect = subprocess.getoutput("docker node inspect " + node)
    dockerNodeInspectJson = json.loads(dockerNodeInspect)
    #print(dockerNodeInspectJson[0]["UpdatedAt"])
    dockerNodeJoinTime = datetime.datetime.strptime(dockerNodeInspectJson[0]["UpdatedAt"][:25],
                                                    '%Y-%m-%dT%H:%M:%S.%f')
    currenTime15MinsAgo = datetime.datetime.now() - datetime.timedelta(minutes = 15)
    #print(currenTime15MinsAgo)
    logger.info("Comparing Node Join Time  in " + node)
    if currenTime15MinsAgo < dockerNodeJoinTime:
        logger.info("Node {node} Joined recently at {jtime}  ".format(node=node,jtime=dockerNodeJoinTime))
        logger.info("Running Rebalance Commands in Services")
        rebalanceService = True
        newNodesJoined.append(node)
    else:
        logger.info("Node not Joined Recently")


#Rebalancing Service If nodes are added recently
if rebalanceService:
    for service in dockerServiceListProcess.splitlines():
        logger.info("Rebalancing Service {servicename}".format(servicename=service))
        dockerRebalanceServiceProcess = subprocess.getoutput(dockerRebalanceService + " " +service )
    logger.success("Services are Rebalanced")
    logger.info("Newly Joined nodes are {nodelist}".format(nodelist=newNodesJoined))
