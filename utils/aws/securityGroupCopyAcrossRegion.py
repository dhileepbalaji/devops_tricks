from boto import ec2
from boto.exception import EC2ResponseError, BotoClientError
from boto.ec2.securitygroup import SecurityGroup
import sys
###Patch the Source code Include VPC and Outbound rules#########
def copy_to_region_vpc(self, region=None, vpc=None, name=None, dry_run=False):
    if region.name == self.region:
        raise BotoClientError('Unable to copy to the same Region')
    conn_params = self.connection.get_params()
    rconn = region.connect(**conn_params)
    conn = region.connect(**conn_params)
    sg = rconn.create_security_group(
        name or self.name,
        self.description,
        vpc,
        dry_run=dry_run
    )
    source_groups = []
    for rule in self.rules:
        for grant in rule.grants:
            grant_nom = grant.name or grant.group_id
            if grant_nom:
                if grant_nom not in source_groups:
                    source_groups.append(grant_nom)
                    sg.authorize(None, None, None, None, grant,
                                 dry_run=dry_run)
            else:
                sg.authorize(rule.ip_protocol, rule.from_port, rule.to_port,
                             grant.cidr_ip, dry_run=dry_run)
    for rule in self.rules_egress:
        for grant in rule.grants:
            try:
                conn.authorize_security_group_egress(sg.id, rule.ip_protocol, rule.from_port, rule.to_port,
                                                          src_group_id=None, cidr_ip=grant.cidr_ip)
            except EC2ResponseError as e:
                if not e.error_code == "InvalidPermission.Duplicate":
                    print(str(e.message))

    return sg


########################################################
SecurityGroup.copy_to_region_vpc = copy_to_region_vpc

####Ec2 Connection######################################
def copy_sg(src_region, dest_region, sg_id, dest_vpc_id, src_ip_address=None, dest_ip_address=None):
    conn = ec2.connect_to_region(src_region)
    conn_dest = ec2.connect_to_region(dest_region)
    sg_list = conn.get_all_security_groups(group_ids=[sg_id])
    sg_name_split = str(sg_list[0]).split(sep=':')
    sg_name = sg_name_split[1]
    f = {'group-name': sg_name, 'vpc-id': dest_vpc_id}
    sg_list[0].copy_to_region_vpc(region=ec2.get_region(dest_region), vpc=dest_vpc_id)
#Replace the IP address source ip with destination IP
    if src_ip_address is not None:
        dest_sg_list = conn_dest.get_all_security_groups(filters=f)
        dest_sg = dest_sg_list[0]
        dest_id = dest_sg.id

        print("----- Started : Replacing Inbound rules -----")
        for rule in sg_list[0].rules:
            for grant in rule.grants:
                try:
                    n = 2
                    groups = grant.cidr_ip.split('.')
                    ipaddress = '.'.join(groups[:n]), '.'.join(groups[n:])
                    if src_ip_address == ipaddress[0]:
                        dest_sg.revoke(rule.ip_protocol, rule.from_port, rule.to_port, grant.cidr_ip)
                except EC2ResponseError as e:
                    if e.error_code == "InvalidPermission.Duplicate":
                        print(str(e.message))
                    else:
                        print(str(e))
        for rule in sg_list[0].rules:
            for grant in rule.grants:
                try:
                    groups = grant.cidr_ip.split('.')
                    ipaddress = '.'.join(groups[:n]), '.'.join(groups[n:])
                    ip_address_dest = dest_ip_address + '.' + ipaddress[1]
                    if src_ip_address == ipaddress[0]:
                        dest_sg.authorize(rule.ip_protocol, rule.from_port, rule.to_port, ip_address_dest)
                except EC2ResponseError as e:
                    if e.error_code == "InvalidPermission.NotFound":
                        print(e)
        print("----- Completed : Replacing Inbound rules -----")
        print("\n----- Started : Replacing Outbound rules ----")
        for rule in sg_list[0].rules_egress:
            for grant in rule.grants:
                try:
                    n = 2
                    groups = grant.cidr_ip.split('.')
                    ipaddress = '.'.join(groups[:n]), '.'.join(groups[n:])
                    if src_ip_address == ipaddress[0]:
                        conn_dest.revoke_security_group_egress(dest_id, rule.ip_protocol, rule.from_port, rule.to_port,
                                                          src_group_id=None, cidr_ip=grant.cidr_ip)
                except EC2ResponseError as e:
                    if e.error_code == "InvalidPermission.Duplicate":
                        print(str(e.message))
                    else:
                        print(str(e.message))
        for rule in sg_list[0].rules_egress:
            for grant in rule.grants:
                try:
                    groups = grant.cidr_ip.split('.')
                    ipaddress = '.'.join(groups[:n]), '.'.join(groups[n:])
                    ip_address_dest = dest_ip_address + '.' + ipaddress[1]
                    if src_ip_address == ipaddress[0]:
                        conn_dest.authorize_security_group_egress(dest_id, rule.ip_protocol, rule.from_port,
                                                                  rule.to_port,
                                                                  src_group_id=None, cidr_ip=ip_address_dest)
                except EC2ResponseError as e:
                    if e.error_code == "InvalidPermission.NotFound":
                        pass

        print("----- Completed : Replacing Outbound rules -----")


#example
#copy_sg('us-west-2','us-west-1','sg-d87702a6','vpc-ac771ccb','172.31','172.16')

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Script to Copy Security Group Across Regions/VPC')
    parser.add_argument(help='Source Region',default=None,dest="src_region")
    parser.add_argument(help='Destination Region',default=None,dest="dest_region")
    parser.add_argument(help='Source Security Group ID',default=None,dest="sg_id")
    parser.add_argument(help='Destination VPC ID',default=None,dest="vpc_id")
    #parser.add_argument(help='Destination SG Name to create, Default: source SG name ', default=None, dest="dest_sg_name")
    parser.add_argument( nargs='?',help='IP address that need to be replaced '
                                                'to Destination IP address while copying SG',default=None,dest="src_ip_address")
    parser.add_argument( nargs='?',help='Destination IP address to replace',default=None,dest="dest_ip_address")
    userinput = parser.parse_args()

    copy_sg(userinput.src_region, userinput.dest_region, userinput.sg_id, userinput.vpc_id, userinput.src_ip_address, userinput.dest_ip_address)
