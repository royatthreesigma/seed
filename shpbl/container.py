"""Docker container operations"""

import docker
import logging
from fastapi import HTTPException
from typing import Optional

from models import ShpblResponse, ContainerName

logger = logging.getLogger(__name__)

# Docker client
docker_client = docker.from_env()

# Container configuration
CONTAINER_WORKDIRS = {"backend": "/backend", "frontend": "/frontend", "db": "/"}


def get_container_workdir(container_name: ContainerName) -> str:
    """Get default working directory for container"""
    return CONTAINER_WORKDIRS.get(container_name, "/")


def exec_in_container(
    container_name: ContainerName, command: str, workdir: Optional[str] = None
) -> ShpblResponse:
    """
    Execute command in specified container

    Args:
        container_name: Name of the container (api, app, db)
        command: Shell command to execute
        workdir: Working directory (defaults to container-specific dir)

    Returns:
        ShpblResponse with success status, exit code, stdout, stderr

    Raises:
        HTTPException: If container not found or execution fails
    """
    try:
        container = docker_client.containers.get(container_name)
        workdir = workdir or get_container_workdir(container_name)

        logger.info(f"Executing in {container_name} ({workdir}): {command}")
        result = container.exec_run(
            cmd=["sh", "-c", command], workdir=workdir, demux=True
        )

        stdout = result.output[0].decode() if result.output[0] else ""
        stderr = result.output[1].decode() if result.output[1] else ""

        return ShpblResponse(
            success=result.exit_code == 0,
            exit_code=result.exit_code,
            stdout=stdout,
            stderr=stderr,
        )
    except docker.errors.NotFound:
        raise HTTPException(
            status_code=404, detail=f"Container '{container_name}' not found"
        )
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(status_code=500, detail=str(e))
