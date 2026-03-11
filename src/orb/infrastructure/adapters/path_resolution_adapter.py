"""Adapter implementing PathResolutionPort using platform_dirs."""

from orb.domain.base.ports.path_resolution_port import PathResolutionPort


class PathResolutionAdapter(PathResolutionPort):
    """Resolves application directory paths using platform-specific logic."""

    def get_config_dir(self) -> str:
        from orb.config.platform_dirs import get_config_location

        return str(get_config_location())

    def get_work_dir(self) -> str:
        from orb.config.platform_dirs import get_work_location

        return str(get_work_location())

    def get_logs_dir(self) -> str:
        from orb.config.platform_dirs import get_logs_location

        return str(get_logs_location())
