"""HostFactory instance type utilities."""


def derive_cpu_ram_from_instance_type(instance_type: str) -> tuple[str, str]:
    """Derive CPU and RAM from instance type for IBM HF attributes.

    Returns (ncpus, nram) as strings, defaulting to ("1", "1024") for unknown types.
    """
    if instance_type == "N/A":
        return "N/A", "N/A"

    cpu_ram_mapping = {
        "t2.micro": ("1", "1024"),
        "t2.small": ("1", "2048"),
        "t2.medium": ("2", "4096"),
        "t2.large": ("2", "8192"),
        "t2.xlarge": ("4", "16384"),
        "t3.micro": ("2", "1024"),
        "t3.small": ("2", "2048"),
        "t3.medium": ("2", "4096"),
        "t3.large": ("2", "8192"),
        "t3.xlarge": ("4", "16384"),
        "m5.large": ("2", "8192"),
        "m5.xlarge": ("4", "16384"),
        "m5.2xlarge": ("8", "32768"),
        "c5.large": ("2", "4096"),
        "c5.xlarge": ("4", "8192"),
        "r5.large": ("2", "16384"),
        "r5.xlarge": ("4", "32768"),
    }

    return cpu_ram_mapping.get(instance_type, ("1", "1024"))
