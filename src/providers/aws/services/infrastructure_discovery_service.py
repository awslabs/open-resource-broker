"""AWS infrastructure discovery service."""

import boto3
from typing import List, Optional

from providers.aws.models.infrastructure_models import VPCInfo, SubnetInfo, SecurityGroupInfo


class AWSInfrastructureDiscoveryService:
    """Service for discovering AWS infrastructure resources."""

    def __init__(self, region: str, profile: Optional[str] = None):
        """Initialize with AWS region and profile."""
        self.region = region
        self.profile = profile
        
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.ec2_client = session.client('ec2', region_name=region)

    def discover_vpcs(self) -> List[VPCInfo]:
        """Discover VPCs in the region."""
        try:
            response = self.ec2_client.describe_vpcs()
            vpcs = []
            
            for vpc in response['Vpcs']:
                name = self._get_name_tag(vpc.get('Tags', []))
                vpcs.append(VPCInfo(
                    id=vpc['VpcId'],
                    name=name or vpc['VpcId'],
                    cidr_block=vpc['CidrBlock'],
                    is_default=vpc.get('IsDefault', False)
                ))
            
            # Sort: default VPC first, then by name
            vpcs.sort(key=lambda v: (not v.is_default, v.name))
            return vpcs
            
        except Exception as e:
            raise RuntimeError(f"Failed to discover VPCs: {e}")

    def discover_subnets(self, vpc_id: str) -> List[SubnetInfo]:
        """Discover subnets in a VPC."""
        try:
            response = self.ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            subnets = []
            for subnet in response['Subnets']:
                name = self._get_name_tag(subnet.get('Tags', []))
                subnets.append(SubnetInfo(
                    id=subnet['SubnetId'],
                    name=name or subnet['SubnetId'],
                    vpc_id=subnet['VpcId'],
                    availability_zone=subnet['AvailabilityZone'],
                    cidr_block=subnet['CidrBlock'],
                    is_public=subnet.get('MapPublicIpOnLaunch', False)
                ))
            
            # Sort by AZ, then public/private
            subnets.sort(key=lambda s: (s.availability_zone, not s.is_public))
            return subnets
            
        except Exception as e:
            raise RuntimeError(f"Failed to discover subnets: {e}")

    def discover_security_groups(self, vpc_id: str) -> List[SecurityGroupInfo]:
        """Discover security groups in a VPC."""
        try:
            response = self.ec2_client.describe_security_groups(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            security_groups = []
            for sg in response['SecurityGroups']:
                rule_summary = self._summarize_sg_rules(sg)
                security_groups.append(SecurityGroupInfo(
                    id=sg['GroupId'],
                    name=sg['GroupName'],
                    description=sg['Description'],
                    vpc_id=sg['VpcId'],
                    rule_summary=rule_summary
                ))
            
            # Sort: default first, then by name
            security_groups.sort(key=lambda sg: (sg.name != 'default', sg.name))
            return security_groups
            
        except Exception as e:
            raise RuntimeError(f"Failed to discover security groups: {e}")

    def _get_name_tag(self, tags: List[dict]) -> Optional[str]:
        """Extract Name tag from AWS tags."""
        for tag in tags:
            if tag.get('Key') == 'Name':
                return tag.get('Value')
        return None

    def _summarize_sg_rules(self, sg: dict) -> str:
        """Create a summary of security group rules."""
        ingress_rules = sg.get('IpPermissions', [])
        if not ingress_rules:
            return "No inbound rules"
        
        if len(ingress_rules) == 1:
            rule = ingress_rules[0]
            if rule.get('IpProtocol') == '-1':
                return "All traffic from VPC"
            port_range = self._get_port_range(rule)
            return f"{port_range} from anywhere" if rule.get('IpRanges') else f"{port_range} from VPC"
        
        return f"{len(ingress_rules)} inbound rules"

    def _get_port_range(self, rule: dict) -> str:
        """Get port range description from security group rule."""
        protocol = rule.get('IpProtocol', '')
        from_port = rule.get('FromPort')
        to_port = rule.get('ToPort')
        
        if protocol == '-1':
            return "All traffic"
        elif from_port == to_port:
            return f"Port {from_port}"
        elif from_port is not None and to_port is not None:
            return f"Ports {from_port}-{to_port}"
        else:
            return protocol.upper()
