"""Interface response DTO for uniform handler return values."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InterfaceResponse:
    data: dict
    exit_code: int = 0
