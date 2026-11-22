"""Standardized CLI exit codes for deterministic AI-agent integration."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Process exit codes returned by the publisher CLI."""

    SUCCESS = 0
    GENERAL_FAILURE = 1
    INVALID_INPUT = 2
    AUTH_FAILURE = 3
    UPLOAD_FAILURE = 4
    DUPLICATE_VIDEO = 5
    REQUIRES_APPROVAL = 6
