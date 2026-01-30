import os
from fastapi import APIRouter
from typing import get_args
import docker

from helpers.file_manager import (
    create_directory,
    create_directory,
    delete_file,
    directory_exists,
    dry_search,
    overwrite_file,
    read_file,
    search,
)
from models import (
    SearchCandidateRequest,
    SearchRequest,
    ReadFileRequest,
    ShpblResponse,
    ContainerName,
    RunCommandRequest,
    ContainerLogsRequest,
    UpdateEnvVariableRequest,
)
from interface import CreateOrOverwriteFile, DeleteFile, ReplaceStringInFile  # type: ignore
from container import exec_in_container


router = APIRouter(prefix="/workspace", tags=["workspace"])

# Docker client for logs
docker_client = docker.from_env()


@router.post("/dry-search", response_model=ShpblResponse)
async def dry_search_workspace(request: SearchCandidateRequest):
    """
    Perform a dry search to get file:line matches without full content.

    Args:
        request: SearchCandidateRequest with extended_regex_query and context_lines

    Returns:
        Dictionary of file paths to line ranges with context
    """
    try:
        dry_run = dry_search(request.extended_regex_query, request.context_lines)
        return ShpblResponse(
            success=True,
            data=dry_run,
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=str(e),
            data={"error": str(e)},
        )


@router.post("/search", response_model=ShpblResponse)
async def search_workspace(request: SearchRequest):
    _errors: list[str] = []
    try:
        search_run: list[str] = search(
            extended_regex_query=request.extended_regex_query,
            context_lines=request.context_lines,
            file_path=request.file_path,
            include_line_numbers=request.include_line_numbers,
        )

        # prune to max_results per request
        is_pruned = False
        if len(search_run) > request.max_results:
            search_run = search_run[: request.max_results]
            is_pruned = True

        # Join results for unparsed response (preserves exact whitespace)
        unparsed_content = "\n---\n".join(search_run) if search_run else ""
        return ShpblResponse(
            message="Search completed" + (" (results pruned)" if is_pruned else ""),
            success=True,
            data={
                "results": search_run,
                "pruned": is_pruned,
            },
            stderr="; ".join(_errors) if _errors else None,
            internal_do_not_parse__=True,
            unparsed_str_response__=unparsed_content,
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=str(e),
            data={"error": str(e)},
        )


@router.post("/read", response_model=ShpblResponse)
async def read_file_workspace(request: ReadFileRequest):
    valid_containers = list(get_args(ContainerName))
    container = request.file_path.split("/")[0]  # get container name only
    assert (
        container in valid_containers
    ), "Container could not be determined from file_path"

    try:
        file_content = read_file(
            container_name=container,
            file_path=request.file_path[
                len(container) + 1 :
            ],  # remove container prefix
            include_line_numbers=request.include_line_numbers,
            start_line=request.start_line,
            end_line=request.end_line,
        )
        return ShpblResponse(
            success=True,
            message="File read successfully",
            data={"file_content": file_content},
            internal_do_not_parse__=True,
            unparsed_str_response__=file_content,
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=str(e),
            data={"error": str(e)},
        )


@router.post("/create-or-overwrite-file", response_model=ShpblResponse)
async def create_or_overwrite_file_workspace(request: CreateOrOverwriteFile):
    valid_containers = list(get_args(ContainerName))
    container = request.file_path.split("/")[0]  # get container name only
    assert (
        container in valid_containers
    ), "Container could not be determined from file_path"

    try:
        # check if directory exists, create if not
        if not directory_exists(
            container, os.path.dirname(request.file_path[len(container) + 1 :])
        ):
            create_directory(
                container, os.path.dirname(request.file_path[len(container) + 1 :])
            )
        # create or overwrite file
        assert overwrite_file(
            container_name=container,
            file_path=request.file_path[len(container) + 1 :],
            content=request.content or "",
        ), "File creation/overwrite failed"
        return ShpblResponse(
            success=True,
            message="File created or overwritten successfully",
            data={"file_path": request.file_path, "status": "created/overwritten"},
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=str(e),
            data={"error": str(e)},
        )


@router.delete("/delete-file", response_model=ShpblResponse)
async def delete_file_workspace(request: DeleteFile):
    valid_containers = list(get_args(ContainerName))
    container = request.file_path.split("/")[0]  # get container name only
    assert (
        container in valid_containers
    ), "Container could not be determined from file_path"

    try:
        # delete file
        assert delete_file(
            container_name=container,
            file_path=request.file_path[len(container) + 1 :],
        ), "File deletion failed"
        return ShpblResponse(
            success=True,
            message="File deleted successfully",
            data={"file_path": request.file_path, "status": "deleted"},
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=str(e),
            data={"error": str(e)},
        )


@router.post("/replace-string-in-file", response_model=ShpblResponse)
async def replace_string_in_file_workspace(request: ReplaceStringInFile):
    valid_containers = list(get_args(ContainerName))
    container = request.file_path.split("/")[0]  # get container name only
    assert (
        container in valid_containers
    ), "Container could not be determined from file_path"

    try:
        # read current file content
        current_content = read_file(
            container_name=container,
            file_path=request.file_path[len(container) + 1 :],
            include_line_numbers=False,
            start_line=1,
            end_line=-1,
        )

        # check if target_string exists exactly once
        occurrences = current_content.count(request.target_string)
        if occurrences == 0:
            return ShpblResponse(
                success=False,
                message="Target string not found in file",
                data={"error": "Target string not found"},
            )
        elif occurrences > 1:
            return ShpblResponse(
                success=False,
                message="Target string found multiple times in file",
                data={"error": "Target string found multiple times"},
            )
        # replace target_string with replacement_string
        new_content = current_content.replace(
            request.target_string, request.replacement_string
        )

        # overwrite file with new content
        assert overwrite_file(
            container_name=container,
            file_path=request.file_path[len(container) + 1 :],
            content=new_content,
        ), "File overwrite failed"

        return ShpblResponse(
            success=True,
            message="String replaced successfully in file",
            data={"file_path": request.file_path, "status": "string replaced"},
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=f"Failed to read file: {str(e)}",
            data={"error": str(e)},
        )


@router.post("/run-command", response_model=ShpblResponse)
async def run_command_in_container(request: RunCommandRequest):
    """
    Execute a raw shell command in the specified container.

    Args:
        request: RunCommandRequest with container_name, command, and optional workdir

    Returns:
        ShpblResponse with success status, stdout, stderr, and exit_code
    """
    try:
        result = exec_in_container(
            container_name=request.container_name, command=request.command
        )
        return result
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=f"Failed to execute command: {str(e)}",
            data={"error": str(e)},
            stderr=str(e),
        )


@router.post("/terminal-logs", response_model=ShpblResponse)
async def get_terminal_logs(request: ContainerLogsRequest):
    """
    Retrieve logs from a specified container, pruned to last 1K characters.

    Args:
        request: ContainerLogsRequest with container_name and num_lines

    Returns:
        ShpblResponse with logs content (pruned to last 1000 characters)
    """
    try:
        # Get container by name
        container = docker_client.containers.get(request.container_name)

        # Get logs (tail by num_lines, decode to string)
        logs = container.logs(tail=request.num_lines).decode("utf-8")

        # Prune to last 1K characters
        if len(logs) > 1000:
            logs = logs[-1000:]
            pruned = True
        else:
            pruned = False

        return ShpblResponse(
            success=True,
            message=f"Container logs retrieved{' (pruned to 1K chars)' if pruned else ''}",
            data={"logs": logs, "pruned": pruned, "character_count": len(logs)},
            internal_do_not_parse__=True,
            unparsed_str_response__=logs,
        )
    except docker.errors.NotFound:
        return ShpblResponse(
            success=False,
            message=f"Container '{request.container_name}' not found",
            data={"error": "Container not found"},
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=f"Failed to retrieve container logs: {str(e)}",
            data={"error": str(e)},
        )


@router.get("/env-variables", response_model=ShpblResponse)
async def get_env_variable_names():
    """
    Get a list of environment variable names from the .env file.
    Does not return values, only variable names.

    Returns:
        ShpblResponse with list of environment variable names
    """
    try:
        env_file_path = "/workspace/.env"

        if not os.path.exists(env_file_path):
            return ShpblResponse(
                success=False,
                message=".env file not found",
                data={"error": ".env file not found"},
            )

        with open(env_file_path, "r") as f:
            lines = f.readlines()

        variable_names = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                # Extract variable name (before '=')
                if "=" in line:
                    var_name = line.split("=", 1)[0].strip()
                    variable_names.append(var_name)

        return ShpblResponse(
            success=True,
            message=f"Found {len(variable_names)} environment variables",
            data={"variable_names": variable_names, "count": len(variable_names)},
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=f"Failed to read .env file: {str(e)}",
            data={"error": str(e)},
        )


@router.post("/env-variables", response_model=ShpblResponse)
async def update_env_variable(request: UpdateEnvVariableRequest):
    """
    Update or create an environment variable in the .env file.
    If the variable exists, it will be updated. If not, it will be added.

    Args:
        request: UpdateEnvVariableRequest with variable_name and value

    Returns:
        ShpblResponse with status of the operation
    """
    try:
        env_file_path = "/workspace/.env"

        # Read existing content
        if os.path.exists(env_file_path):
            with open(env_file_path, "r") as f:
                lines = f.readlines()
        else:
            lines = []

        # Find and update existing variable or add new one
        variable_found = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            # Check if this line contains our variable
            if stripped and not stripped.startswith("#") and "=" in stripped:
                var_name = stripped.split("=", 1)[0].strip()
                if var_name == request.variable_name:
                    # Update existing variable
                    new_lines.append(f"{request.variable_name}={request.value}\n")
                    variable_found = True
                else:
                    new_lines.append(line)
            else:
                # Keep comments and empty lines as-is
                new_lines.append(line)

        # If variable wasn't found, add it at the end
        if not variable_found:
            # Add newline before if file doesn't end with one
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            new_lines.append(f"{request.variable_name}={request.value}\n")

        # Write back to file
        with open(env_file_path, "w") as f:
            f.writelines(new_lines)

        return ShpblResponse(
            success=True,
            message=f"Environment variable '{request.variable_name}' {'updated' if variable_found else 'created'} successfully",
            data={
                "variable_name": request.variable_name,
                "status": "updated" if variable_found else "created",
            },
        )
    except Exception as e:
        return ShpblResponse(
            success=False,
            message=f"Failed to update .env file: {str(e)}",
            data={"error": str(e)},
        )
