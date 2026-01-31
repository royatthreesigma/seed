#!/usr/bin/env bash
set -euo pipefail

# Log everything
exec > >(tee -a /var/log/startup-script.log) 2>&1
echo "=== boot_script started: $(date -Is) ==="

MOUNT_DIR="${MOUNT_DIR:-/mnt}"
APP_DIR="${MOUNT_DIR}/code"

# Store env in a persistent, non-git-tracked location on the volume
ENV_DIR="${MOUNT_DIR}/config"
PERSIST_ENV_FILE="${ENV_DIR}/seed.env"

# The app expects .env in the repo; we'll symlink to the persistent env file
APP_ENV_LINK="${APP_DIR}/.env"

rand_str() {
  local len="${1:-16}"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$(( (len + 1) / 2 ))" | head -c "$len"
  else
    tr -dc 'a-zA-Z0-9' </dev/urandom | head -c "$len"
  fi
}

# Verify app dir exists (should be cloned by user_data)
if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: App dir not found at $APP_DIR"
  echo "The repo should be cloned by user_data before this script runs."
  exit 1
fi

# Create persistent env ONCE, reuse afterwards
mkdir -p "$ENV_DIR"

if [ ! -f "$PERSIST_ENV_FILE" ]; then
  echo "No existing env found. Generating and saving: $PERSIST_ENV_FILE"

  DB_NAME="db_$(rand_str 10)"
  DB_USER="user_$(rand_str 10)"
  DB_PASS="$(rand_str 24)"
  DJANGO_SECRET_KEY="$(rand_str 50)"

  cat > "$PERSIST_ENV_FILE" <<EOF
ENVIRONMENT=development
POSTGRES_DB=${DB_NAME}
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_USER=${DB_USER}
POSTGRES_HOST=db
POSTGRES_PORT=5432
DEBUG=true
SECRET_KEY=${DJANGO_SECRET_KEY}
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key_here
CLERK_SECRET_KEY=your_clerk_secret_here
RESEND_API_KEY=your_resend_api_key_here
EOF

  chmod 600 "$PERSIST_ENV_FILE"
else
  echo "Reusing existing env: $PERSIST_ENV_FILE"
fi

# Ensure the app sees .env (symlink to persistent file)
if [ -e "$APP_ENV_LINK" ] && [ ! -L "$APP_ENV_LINK" ]; then
  echo "WARNING: $APP_ENV_LINK exists and is not a symlink. Leaving it untouched."
elif [ ! -L "$APP_ENV_LINK" ]; then
  ln -sf "$PERSIST_ENV_FILE" "$APP_ENV_LINK"
fi

# Start services
cd "$APP_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found. Install Docker first."
  exit 1
fi

docker compose up -d

echo "=== Startup complete: $(date -Is) ==="
