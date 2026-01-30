import os
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List

# Type aliases
ContainerName = Literal["backend", "frontend", "db"]


class SearchCandidateRequest(BaseModel):
    """Request model for searching candidates in the workspace"""

    extended_regex_query: str = Field(..., description="Search query (regex supported)")
    context_lines: int = Field(
        5, description="Number of context lines before/after match"
    )


class SearchRequest(BaseModel):
    """Request model for workspace search"""

    extended_regex_query: str = Field(..., description="Search query (regex supported)")
    max_results: int = Field(100, description="Maximum results per search")
    context_lines: int = Field(
        5, description="Number of context lines before/after match"
    )
    file_path: str = Field(
        pattern=r"^(frontend|backend)/.*",
        description="Optional file path to limit the search to",
    )
    include_line_numbers: bool = Field(
        description="Whether to include line numbers in results"
    )


class ReadFileRequest(BaseModel):
    """Request model for reading files"""

    file_path: str = Field(..., description="Path to file relative to container root")
    include_line_numbers: bool = Field(
        description="Whether to include line numbers in the output"
    )
    start_line: int = Field(
        ge=1, description="Starting line number to read from (1-based)"
    )
    end_line: int = Field(
        description="Ending line number to read to (inclusive). If -1, reads to end of file.",
    )


class ContainerLogsRequest(BaseModel):
    container_name: ContainerName = Field(
        ..., description="Name of the container to get logs from"
    )
    num_lines: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Number of lines to retrieve from the end of the logs (default: 50, max: 500)",
    )


class ShpblResponse(BaseModel):
    """Unified response model for all shpbl operations"""

    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None

    # HACK: for use when we want to bypass parsing at any place in the pipeline
    # useful when string matching is needed for LLMs
    internal_do_not_parse__: bool = False
    unparsed_str_response__: Optional[str] = None


class DjangoAppRequest(BaseModel):
    app_name: str
    base_url: Optional[str] = None


class RunCommandRequest(BaseModel):
    """Request model for running raw commands in a container"""

    container_name: ContainerName = Field(
        ..., description="Name of the container to run the command in"
    )
    command: str = Field(..., description="Raw shell command to execute")


class UpdateEnvVariableRequest(BaseModel):
    """Request model for updating or creating environment variables"""

    variable_name: str = Field(..., description="Name of the environment variable")
    value: str = Field(..., description="Value of the environment variable")
