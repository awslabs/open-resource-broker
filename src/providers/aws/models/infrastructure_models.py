"""AWS infrastructure models for discovery and selection."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VPCInfo:
    """VPC information for selection."""
    id: str
    name: str
    cidr_block: str
    is_default: bool

    def __str__(self) -> str:
        default_marker = " (default)" if self.is_default else ""
        return f"{self.id}{default_marker} - {self.cidr_block}"


@dataclass
class SubnetInfo:
    """Subnet information for selection."""
    id: str
    name: str
    vpc_id: str
    availability_zone: str
    cidr_block: str
    is_public: bool

    def __str__(self) -> str:
        subnet_type = "public" if self.is_public else "private"
        return f"{self.id} ({self.availability_zone}) - {self.cidr_block} ({subnet_type})"


@dataclass
class SecurityGroupInfo:
    """Security group information for selection."""
    id: str
    name: str
    description: str
    vpc_id: str
    rule_summary: str

    def __str__(self) -> str:
        return f"{self.id} ({self.name}) - {self.rule_summary}"
