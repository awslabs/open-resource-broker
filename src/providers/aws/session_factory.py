"""AWS Session Factory - Centralized boto3 session creation."""

from typing import Optional

import boto3


class AWSSessionFactory:
    """Factory for creating AWS sessions with credential chain fallback."""

    @staticmethod
    def create_session(
        profile: Optional[str] = None, region: Optional[str] = None
    ) -> boto3.Session:
        """Create AWS session with credential chain fallback.

        Args:
            profile: AWS profile name (optional)
            region: AWS region (optional)

        Returns:
            Configured boto3 session
        """
        if profile:
            return boto3.Session(profile_name=profile, region_name=region)
        else:
            return boto3.Session(region_name=region)

    @staticmethod
    def discover_credentials(profile: Optional[str] = None, region: Optional[str] = None) -> dict:
        """Discover AWS credentials and return metadata.

        Args:
            profile: AWS profile name (optional)
            region: AWS region (optional)

        Returns:
            Dict with success status and credential metadata
        """
        try:
            session = AWSSessionFactory.create_session(profile, region)
            identity = session.client("sts").get_caller_identity()
            return {
                "success": True,
                "profile": profile,
                "region": session.region_name,
                "account": identity["Account"],
                "identity": identity["Arn"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
