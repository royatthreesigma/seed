from typing import List, Literal, Optional, TypedDict, Any, Dict

from pydantic import BaseModel, Field

ContainerName = Literal["frontend", "backend"]


class CreateOrOverwriteFile(BaseModel):
    file_path: str = Field(
        ...,
        pattern=r"^(frontend|backend)/.*",
        description="Path to the file being modified (must start with 'frontend/' or 'backend/'). Will be created if it does not exist.",
    )
    content: str = Field(
        ...,
        description="New content for overwrite_file and create_new_file operations",
    )


class DeleteFile(BaseModel):
    file_path: str = Field(
        ...,
        pattern=r"^(frontend|backend)/.*",
        description="Path to the file being deleted (must start with 'frontend/' or 'backend/').",
    )


class ReplaceStringInFile(BaseModel):
    file_path: str = Field(
        ...,
        pattern=r"^(frontend|backend)/.*",
        description="Path to the file being modified (must start with 'frontend/' or 'backend/').",
    )
    target_string: str = Field(
        ...,
        description="The string to be replaced in the file. Must be exact match. Must exist exactly once in the file. Should not include line numbers.",
    )
    replacement_string: str = Field(
        ...,
        description="The string to replace the target string with. Should not include line numbers.",
    )


class ServiceCheck(BaseModel):
    """Individual service health check result"""

    name: str = Field(..., description="Display name of the service")
    description: str = Field(..., description="Description of what the service does")
    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ..., description="Health status of the service"
    )
    latency: str = Field(
        ..., description="Response latency with unit (e.g., '12.34ms')"
    )
    message: Optional[str] = Field(
        None, description="Additional information or error message"
    )


class HealthCheckResponse(BaseModel):
    """
    Comprehensive health check response for the entire stack.

    Attributes:
        status: Overall system health status
        service: Service identifier
        version: Service version
        timestamp: ISO 8601 UTC timestamp of the health check
        uptime: Human-readable uptime (e.g., '2h 15m')
        checks: Dictionary of service health checks keyed by service ID
        totalLatency: Total time taken for all health checks with unit
    """

    status: Literal["healthy", "unhealthy"] = Field(
        ..., description="Overall system health status"
    )
    service: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    uptime: str = Field(..., description="Human-readable uptime (e.g., '2h 15m')")
    checks: Dict[str, ServiceCheck] = Field(
        ..., description="Dictionary of service health checks"
    )
    totalLatency: str = Field(
        ..., description="Total health check duration with unit (e.g., '147.23ms')"
    )
