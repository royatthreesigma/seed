import json
from typing_extensions import get_args
from fastapi import FastAPI  # type: ignore
import logging
import httpx
import docker  # type: ignore
import os
import time
import zipfile
from pathlib import Path
import yaml
from io import BytesIO
from fastapi import Response
from datetime import datetime, timezone
from typing import Dict, Any
from container import exec_in_container
from helpers.file_scripts import GET_FILE_LIST_NODE, GET_FILE_LIST_PYTHON
from helpers.helpers import DIRECTORIES_TO_EXCLUDE, FILES_TO_EXCLUDE
from routers import api_service, app_service, workspace_service, db_service  # type: ignore
from interface import HealthCheckResponse, ServiceCheck  # type: ignore
from models import ContainerName, ShpblResponse  # type: ignore


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service metadata
SERVICE_VERSION = "0.1.0"
SERVICE_START_TIME = time.time()

# Initialize FastAPI app
app = FastAPI(
    title="Shpbl Manager Service",
    description="Manages file edits and shell execution across backend, app, and db containers",
    version=SERVICE_VERSION,
)

# Include service routers
app.include_router(api_service.router)
app.include_router(app_service.router)
app.include_router(workspace_service.router)
app.include_router(db_service.router)


@app.get("/")
async def root():
    return {"message": "Shpbl Manager Service", "version": SERVICE_VERSION}


@app.get("/health", response_model=ShpblResponse)
async def health_check() -> ShpblResponse:
    """Comprehensive health check for the entire stack"""
    start_time = time.time()
    docker_client = docker.from_env()

    # Get actual container uptime
    try:
        shpbl_container = docker_client.containers.get("shpbl")
        container_started_at = shpbl_container.attrs["State"]["StartedAt"]
        # Parse ISO timestamp and calculate uptime
        started_time = datetime.fromisoformat(
            container_started_at.replace("Z", "+00:00")
        )
        uptime_seconds = int(
            (datetime.now(timezone.utc) - started_time).total_seconds()
        )
    except Exception as e:
        logger.warning(f"Could not get container uptime: {e}")
        uptime_seconds = int(time.time() - SERVICE_START_TIME)

    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24

    if uptime_days > 0:
        uptime_display = f"{uptime_days}d {uptime_hours % 24}h {uptime_minutes % 60}m"
    elif uptime_hours > 0:
        uptime_display = (
            f"{uptime_hours}h {uptime_minutes % 60}m {uptime_seconds % 60}s"
        )
    elif uptime_minutes > 0:
        uptime_display = f"{uptime_minutes}m {uptime_seconds % 60}s"
    else:
        uptime_display = f"{uptime_seconds}s"

    checks: Dict[str, ServiceCheck] = {}
    overall_healthy = True

    # Check shpbl service itself
    self_check_start = time.time()
    checks["agent"] = ServiceCheck(
        name="Agent Service",
        description="Core orchestration and container management service",
        status="healthy",
        latency=f"{round((time.time() - self_check_start) * 1000, 2)}ms",
    )

    # Check database container
    db_check_start = time.time()
    try:
        db_container = docker_client.containers.get("db")
        db_status = db_container.status

        if db_status == "running":
            result = db_container.exec_run(
                cmd=["pg_isready", "-U", "postgres"], demux=True
            )
            latency = f"{round((time.time() - db_check_start) * 1000, 2)}ms"
            if result.exit_code == 0:
                checks["database"] = ServiceCheck(
                    name="Database",
                    description="PostgreSQL database service",
                    status="healthy",
                    latency=latency,
                )
            else:
                checks["database"] = ServiceCheck(
                    name="Database",
                    description="PostgreSQL database service",
                    status="unhealthy",
                    latency=latency,
                    message="Database not accepting connections",
                )
                overall_healthy = False
        else:
            checks["database"] = ServiceCheck(
                name="Database",
                description="PostgreSQL database service",
                status="unhealthy",
                latency=f"{round((time.time() - db_check_start) * 1000, 2)}ms",
                message="Container not running",
            )
            overall_healthy = False
    except docker.errors.NotFound:
        checks["database"] = ServiceCheck(
            name="Database",
            description="PostgreSQL database service",
            status="unhealthy",
            latency=f"{round((time.time() - db_check_start) * 1000, 2)}ms",
            message="Service unavailable",
        )
        overall_healthy = False
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        checks["database"] = ServiceCheck(
            name="Database",
            description="PostgreSQL database service",
            status="unhealthy",
            latency=f"{round((time.time() - db_check_start) * 1000, 2)}ms",
            message="Health check failed",
        )
        overall_healthy = False

    # Check backend service
    api_check_start = time.time()
    try:
        backend_container = docker_client.containers.get("backend")
        backend_status = backend_container.status

        if backend_status == "running":
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get("http://backend:8000/")
                    latency = f"{round((time.time() - api_check_start) * 1000, 2)}ms"
                    if response.status_code in [200, 404]:
                        checks["api"] = ServiceCheck(
                            name="API Service",
                            description="Backend REST API service",
                            status="healthy",
                            latency=latency,
                        )
                    else:
                        checks["api"] = ServiceCheck(
                            name="API Service",
                            description="Backend REST API service",
                            status="degraded",
                            latency=latency,
                            message=f"Responded with status {response.status_code}",
                        )
                        overall_healthy = False
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    logger.error(f"Backend health check error: {e}")
                    checks["api"] = ServiceCheck(
                        name="API Service",
                        description="Backend REST API service",
                        status="unhealthy",
                        latency=f"{round((time.time() - api_check_start) * 1000, 2)}ms",
                        message="Service not responding",
                    )
                    overall_healthy = False
        else:
            checks["api"] = ServiceCheck(
                name="API Service",
                description="Backend REST API service",
                status="unhealthy",
                latency=f"{round((time.time() - api_check_start) * 1000, 2)}ms",
                message="Container not running",
            )
            overall_healthy = False
    except docker.errors.NotFound:
        checks["api"] = ServiceCheck(
            name="API Service",
            description="Backend REST API service",
            status="unhealthy",
            latency=f"{round((time.time() - api_check_start) * 1000, 2)}ms",
            message="Service unavailable",
        )
        overall_healthy = False
    except Exception as e:
        logger.error(f"Backend health check error: {e}")
        checks["api"] = ServiceCheck(
            name="API Service",
            description="Backend REST API service",
            status="unhealthy",
            latency=f"{round((time.time() - api_check_start) * 1000, 2)}ms",
            message="Health check failed",
        )
        overall_healthy = False

    # Check frontend service
    web_check_start = time.time()
    try:
        frontend_container = docker_client.containers.get("frontend")
        frontend_status = frontend_container.status

        if frontend_status == "running":
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get("http://frontend:3000")
                    latency = f"{round((time.time() - web_check_start) * 1000, 2)}ms"
                    if response.status_code == 200:
                        checks["web"] = ServiceCheck(
                            name="Web Service",
                            description="Frontend web application",
                            status="healthy",
                            latency=latency,
                        )
                    else:
                        checks["web"] = ServiceCheck(
                            name="Web Service",
                            description="Frontend web application",
                            status="degraded",
                            latency=latency,
                            message=f"Responded with status {response.status_code}",
                        )
                        overall_healthy = False
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    logger.error(f"Frontend health check error: {e}")
                    checks["web"] = ServiceCheck(
                        name="Web Service",
                        description="Frontend web application",
                        status="unhealthy",
                        latency=f"{round((time.time() - web_check_start) * 1000, 2)}ms",
                        message="Service not responding",
                    )
                    overall_healthy = False
        else:
            checks["web"] = ServiceCheck(
                name="Web Service",
                description="Frontend web application",
                status="unhealthy",
                latency=f"{round((time.time() - web_check_start) * 1000, 2)}ms",
                message="Container not running",
            )
            overall_healthy = False
    except docker.errors.NotFound:
        checks["web"] = ServiceCheck(
            name="Web Service",
            description="Frontend web application",
            status="unhealthy",
            latency=f"{round((time.time() - web_check_start) * 1000, 2)}ms",
            message="Service unavailable",
        )
        overall_healthy = False
    except Exception as e:
        logger.error(f"Frontend health check error: {e}")
        checks["web"] = ServiceCheck(
            name="Web Service",
            description="Frontend web application",
            status="unhealthy",
            latency=f"{round((time.time() - web_check_start) * 1000, 2)}ms",
            message="Health check failed",
        )
        overall_healthy = False

    # Build health check response
    health_response = HealthCheckResponse(
        status="healthy" if overall_healthy else "unhealthy",
        service="agent",
        version=SERVICE_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime=uptime_display,
        checks=checks,
        totalLatency=f"{round((time.time() - start_time) * 1000, 2)}ms",
    )

    # Return unified ShpblResponse with health check data
    return ShpblResponse(
        success=overall_healthy,
        message="Health check completed",
        data=health_response.model_dump(),
    )


@app.post("/validate", response_model=ShpblResponse)
async def validate_code():
    """
    Run validation checks on backend and frontend containers.

    Backend: Runs Django's `python manage.py check --fail-level ERROR`
    Frontend: Runs TypeScript check with `npx tsc --noEmit`

    Returns:
        ShpblResponse with validation results for each container
    """
    validation_results = {}
    errors = []

    # Backend validation (Django check)
    backend_check_cmd = "python manage.py check --fail-level ERROR"
    backend_check_result = exec_in_container("backend", backend_check_cmd)
    backend_output = (backend_check_result.stdout or "") + (
        backend_check_result.stderr or ""
    )
    validation_results["backend"] = {
        "command": backend_check_cmd,
        "success": backend_check_result.success,
        "output": backend_output.strip(),
    }
    if not backend_check_result.success:
        errors.append(f"Backend validation failed: {backend_output.strip()}")

    # Frontend validation (TypeScript check)
    frontend_check_cmd = "npx tsc --noEmit"
    frontend_check_result = exec_in_container("frontend", frontend_check_cmd)
    frontend_output = (frontend_check_result.stdout or "") + (
        frontend_check_result.stderr or ""
    )
    validation_results["frontend"] = {
        "command": frontend_check_cmd,
        "success": frontend_check_result.success,
        "output": frontend_output.strip(),
    }
    if not frontend_check_result.success:
        errors.append(f"Frontend validation failed: {frontend_output.strip()}")

    # Determine overall success
    all_checks_passed = all(v["success"] for v in validation_results.values())

    message = "Validation checks completed"
    if all_checks_passed:
        message += " - all checks passed"
    else:
        message += " - some checks failed"

    return ShpblResponse(
        success=all_checks_passed,
        message=message,
        data=validation_results,
        stderr="; ".join(errors) if errors else None,
    )


@app.post("/reload", response_model=ShpblResponse)
async def reload_containers():
    """
    Restart frontend, backend, and database containers.

    Returns:
        ShpblResponse with restart results for each container
    """
    docker_client = docker.from_env()
    reload_results = {}
    errors = []

    containers_to_reload = ["frontend", "backend", "db"]

    for container_name in containers_to_reload:
        try:
            container = docker_client.containers.get(container_name)
            logger.info(f"Restarting {container_name} container...")
            container.restart(timeout=10)
            reload_results[container_name] = {
                "success": True,
                "message": f"{container_name} container restarted successfully",
            }
        except docker.errors.NotFound:
            error_msg = f"{container_name} container not found"
            logger.error(error_msg)
            reload_results[container_name] = {"success": False, "message": error_msg}
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to restart {container_name}: {str(e)}"
            logger.error(error_msg)
            reload_results[container_name] = {"success": False, "message": error_msg}
            errors.append(error_msg)

    all_successful = all(v["success"] for v in reload_results.values())

    message = "Container reload completed"
    if all_successful:
        message += " - all containers restarted successfully"
    else:
        message += " - some containers failed to restart"

    return ShpblResponse(
        success=all_successful,
        message=message,
        data=reload_results,
        stderr="; ".join(errors) if errors else None,
    )


@app.get("/filetree", response_model=ShpblResponse)
async def get_workspace_filetree():
    """
    Get flat list of all files from all containers (backend, frontend).

    Args:
        source_only: If True, only include source code files

    Returns:
        Flat list of files from all containers
    """
    containers = list(get_args(ContainerName))
    combined_data = {}
    errors = []

    source_arg = "True"

    # Escape scripts
    escaped_python = GET_FILE_LIST_PYTHON.replace("'", "'\\''")
    escaped_node = GET_FILE_LIST_NODE.replace("'", "'\\''")

    # Container-specific commands
    container_commands = {
        "backend": f"python -c '{escaped_python}' {source_arg}",
        "frontend": f"node -e '{escaped_node}' {source_arg}",
    }

    # Get file list from each container
    for container in containers:
        cmd = container_commands.get(container)

        if cmd is None:
            # Skip containers that shouldn't have file trees
            continue

        result = exec_in_container(container, cmd)

        if result.success:
            try:
                file_list = json.loads(result.stdout)
                # Prefix each file path with container name
                prefixed_files = [f"{container}/{f}" for f in file_list]
                combined_data[container] = prefixed_files
            except json.JSONDecodeError as e:
                errors.append(f"{container}: Failed to parse JSON - {str(e)}")
        else:
            errors.append(f"{container}: {result.stderr or 'Command failed'}")

    # Determine overall success
    success = len(combined_data) > 0 and not all(
        "error" in v for v in combined_data.values()
    )
    message = "File tree retrieved from all containers"
    if errors:
        message += f" (with errors: {'; '.join(errors)})"

    return ShpblResponse(
        success=success,
        message=message,
        data=combined_data,
    )


@app.get("/routes", response_model=ShpblResponse)
async def get_routes():
    # use "python manage.py show_urls" for the backend to get all routes
    # use "find app -name 'page.*'" for the frontend to get all routes
    backend_cmd = "python manage.py show_urls"
    frontend_cmd = "find app -name 'page.*'"
    combined_data = {}
    errors = []

    # Backend routes
    backend_result = exec_in_container("backend", backend_cmd)
    if backend_result.success:
        try:
            combined_data["backend"] = backend_result.stdout.splitlines()
        except json.JSONDecodeError as e:
            errors.append(
                f"backend: Failed to parse JSON - {backend_result.model_dump_json()}"
            )
    else:
        errors.append(f"backend: {backend_result.stderr or 'Command failed'}")

    # Frontend routes
    frontend_result = exec_in_container("frontend", frontend_cmd)
    if frontend_result.success:
        file_paths = [
            line.strip() for line in frontend_result.stdout.splitlines() if line.strip()
        ]
        # Convert file paths to routes
        frontend_routes = []
        for path in file_paths:
            route = (
                path[len("app/") :]
                .replace("/page.tsx", "")
                .replace("page.tsx", "")
                .replace("/page.jsx", "")
                .replace("page.jsx", "")
            )
            route = "/" + route if route else "/"
            frontend_routes.append(route)
        combined_data["frontend"] = frontend_routes
    else:
        errors.append(f"frontend: {frontend_result.stderr or 'Command failed'}")

    success = len(combined_data) > 0 and not all(
        "error" in v for v in combined_data.values()
    )
    message = "Routes retrieved from containers"
    if errors:
        message += f" (with errors: {'; '.join(errors)})"
    return ShpblResponse(
        success=success,
        message=message,
        data=combined_data,
    )


@app.get("/download-zip")
async def download_workspace_zip():
    """
    Create and download a zip of the entire workspace, excluding:
    - env/, node_modules/, .env files
    - The shpbl service directory
    - Docker/git metadata

    Also modifies compose.yaml to remove the shpbl service entry.
    """
    try:
        workspace_root = Path("/workspace")
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"workspace-{timestamp}.zip"

        # Add shpbl and nginx to exclusions
        exclude_dirs = DIRECTORIES_TO_EXCLUDE | {"shpbl", "nginx"}
        exclude_files = FILES_TO_EXCLUDE | {"boot_script.sh"}

        # Create zip in memory
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(workspace_root):
                # Filter out excluded directories in-place
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for file in files:
                    # Skip excluded files
                    if file in exclude_files:
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(workspace_root)

                    # Special handling for compose.yaml: remove shpbl service
                    if file == "compose.yaml":
                        with open(file_path, "r") as f:
                            compose_data = yaml.safe_load(f)

                        # Remove orchestration services
                        if compose_data and "services" in compose_data:
                            if "shpbl" in compose_data["services"]:
                                del compose_data["services"]["shpbl"]
                            if "proxy" in compose_data["services"]:
                                del compose_data["services"]["proxy"]

                        # Write modified compose.yaml to zip
                        modified_content = yaml.dump(
                            compose_data, default_flow_style=False, sort_keys=False
                        )
                        zipf.writestr(str(arcname), modified_content)
                    else:
                        # Regular files: add as-is
                        zipf.write(file_path, arcname)

        return Response(
            content=buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        return ShpblResponse(
            success=False,
            message=f"Failed to create workspace zip: {str(e)}",
            data={"error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
