import os
import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Dict, Any, List

# Type aliases
ContainerName = Literal["backend", "frontend"]

# Blocked command patterns — matches are case-insensitive substring/regex checks
# against the raw command string before it reaches the container.
BLOCKED_COMMAND_PATTERNS: list[re.Pattern] = [
    # Secret / env leaking
    re.compile(r"\benv\b", re.IGNORECASE),
    re.compile(r"\bprintenv\b", re.IGNORECASE),
    re.compile(r"\bcat\s+\.env\b", re.IGNORECASE),
    re.compile(r"/etc/shadow", re.IGNORECASE),
    re.compile(r"/etc/passwd", re.IGNORECASE),
    # Container / network escape
    re.compile(r"\bdocker\b", re.IGNORECASE),
    re.compile(r"\bcurl\b", re.IGNORECASE),
    re.compile(r"\bwget\b", re.IGNORECASE),
    re.compile(r"\bnc\b", re.IGNORECASE),
    re.compile(r"\bncat\b", re.IGNORECASE),
    re.compile(r"\bnetcat\b", re.IGNORECASE),
    re.compile(r"\bssh\b", re.IGNORECASE),
    re.compile(r"\bscp\b", re.IGNORECASE),
    re.compile(r"\bnsenter\b", re.IGNORECASE),
    re.compile(r"\bsocat\b", re.IGNORECASE),
    # Path traversal / system access
    re.compile(r"\.\./\.\.", re.IGNORECASE),          # ../../
    re.compile(r"/proc\b", re.IGNORECASE),
    re.compile(r"/sys\b", re.IGNORECASE),
    re.compile(r"/var/run/docker\.sock", re.IGNORECASE),
]


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

    @field_validator("command")
    @classmethod
    def validate_command_safety(cls, v: str) -> str:
        for pattern in BLOCKED_COMMAND_PATTERNS:
            if pattern.search(v):
                raise ValueError(
                    f"Command blocked: matches restricted pattern '{pattern.pattern}'"
                )
        return v


class UpdateEnvVariableRequest(BaseModel):
    """Request model for updating or creating environment variables"""

    variable_name: str = Field(..., description="Name of the environment variable")
    value: str = Field(..., description="Value of the environment variable")
