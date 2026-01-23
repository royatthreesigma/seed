from fastapi import APIRouter

from models import DjangoAppRequest, ShpblResponse
from container import exec_in_container
from helpers.django_scripts import (
    CREATE_URLS_SCRIPT,
    INCLUDE_URLS_SCRIPT,
    ADD_INSTALLED_APP_SCRIPT,
)

router = APIRouter(prefix="/api", tags=["backend"])


def run_python_script(script: str, *args: str) -> ShpblResponse:
    """Execute a Python script inside the backend container with arguments"""
    # Write script to temp file and execute with args
    escaped_script = script.replace("'", "'\\''")
    args_str = " ".join(f"'{arg}'" for arg in args)
    cmd = f"python -c '{escaped_script}' {args_str}"
    return exec_in_container("backend", cmd)


@router.post("/django/app", response_model=ShpblResponse)
async def create_django_app(request: DjangoAppRequest):
    """Create a new Django app in the backend container"""
    app_name = request.app_name
    base_url = request.base_url or f"{app_name}/"

    # Normalize base_url
    base_url = base_url.lstrip("/")
    if not base_url.endswith("/"):
        base_url += "/"

    # Step 1: Create the Django app
    result1 = exec_in_container("backend", f"python manage.py startapp {app_name}")
    if not result1.success:
        return ShpblResponse(
            success=False,
            message=f"Failed to create Django app '{app_name}'",
            stdout=result1.stdout,
            stderr=result1.stderr,
            exit_code=result1.exit_code,
        )

    # Step 2: Create urls.py in the new app
    result2 = run_python_script(CREATE_URLS_SCRIPT, app_name)
    if not result2.success:
        return ShpblResponse(
            success=False,
            message="App created but failed to create urls.py",
            stdout=result2.stdout,
            stderr=result2.stderr,
            exit_code=result2.exit_code,
        )

    # Step 3: Add URL include to config/urls.py
    result3 = run_python_script(INCLUDE_URLS_SCRIPT, app_name, base_url)
    if not result3.success:
        return ShpblResponse(
            success=False,
            message="App and urls.py created but failed to wire URLs",
            stdout=result3.stdout,
            stderr=result3.stderr,
            exit_code=result3.exit_code,
        )

    # Step 4: Add to INSTALLED_APPS
    result4 = run_python_script(ADD_INSTALLED_APP_SCRIPT, app_name)
    if not result4.success:
        return ShpblResponse(
            success=False,
            message="App created but failed to add to INSTALLED_APPS",
            stdout=result4.stdout,
            stderr=result4.stderr,
            exit_code=result4.exit_code,
        )

    return ShpblResponse(
        success=True,
        message=f"Django app '{app_name}' created and wired successfully!",
        data={
            "app_name": app_name,
            "url": f"/{base_url}",
            "urls_created": True,
            "installed_apps_updated": True,
        },
        stdout=f"{result1.stdout}\n{result2.stdout}\n{result3.stdout}\n{result4.stdout}",
    )


@router.post("/django/migrate", response_model=ShpblResponse)
async def run_migrations():
    """Create and apply Django migrations"""
    commands = ["python manage.py makemigrations", "python manage.py migrate"]

    result = exec_in_container("backend", " && ".join(commands))

    return ShpblResponse(
        success=result.success,
        message="Migrations completed" if result.success else "Migration failed",
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
    )


@router.post("/django/check-migrations")
async def check_migrations():
    """Check for pending Django migrations"""
    result = exec_in_container(
        "backend", "python manage.py makemigrations --dry-run --check"
    )

    has_changes = result.exit_code == 1
    return ShpblResponse(
        success=True,
        message=(
            "Changes detected - migrations needed"
            if has_changes
            else "No changes detected"
        ),
        data={"has_changes": has_changes},
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
    )


@router.post("/django/reset-db", response_model=ShpblResponse)
async def reset_database():
    """Reset database completely (WARNING: Deletes all data!)"""
    reset_script = """
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('DROP SCHEMA public CASCADE;')
    cursor.execute('CREATE SCHEMA public;')
    cursor.execute('GRANT ALL ON SCHEMA public TO public;')
"
"""

    # Step 1: Drop schema
    result1 = exec_in_container("backend", reset_script)
    if not result1.success:
        return ShpblResponse(
            success=False,
            message="Failed to drop schema",
            stdout=result1.stdout,
            stderr=result1.stderr,
            exit_code=result1.exit_code,
        )

    # Step 2: Clean migrations
    clean_cmd = "find . -path '*/migrations/*.py' -not -name '__init__.py' -delete"
    exec_in_container("backend", clean_cmd)

    # Step 3: Recreate migrations
    result2 = exec_in_container(
        "backend", "python manage.py makemigrations && python manage.py migrate"
    )

    return ShpblResponse(
        success=result2.success,
        message=(
            "Database reset successfully"
            if result2.success
            else "Reset completed but migrations failed"
        ),
        stdout=result2.stdout,
        stderr=result2.stderr,
        exit_code=result2.exit_code,
    )
