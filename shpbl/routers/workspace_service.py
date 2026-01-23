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
)
from interface import CreateOrOverwriteFile, DeleteFile, ReplaceStringInFile  # type: ignore


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

        return ShpblResponse(
            message="Search completed" + (" (results pruned)" if is_pruned else ""),
            success=True,
            data={
                "results": search_run,
                "pruned": is_pruned,
            },
            stderr="; ".join(_errors) if _errors else None,
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
