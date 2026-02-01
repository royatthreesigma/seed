#!/usr/bin/env bash
set -euo pipefail

# Log everything
exec > >(tee -a /var/log/startup-script.log) 2>&1
echo "=== boot_script started: $(date -Is) ==="

MOUNT_DIR="${MOUNT_DIR:-/mnt}"
APP_DIR="${MOUNT_DIR}/code"
ENV_FILE="${APP_DIR}/.env"

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

# Create env ONCE, preserve on subsequent boots to keep DB credentials
if [ -f "$ENV_FILE" ]; then
  echo "Reusing existing .env file (preserving credentials)"
else
  echo "No .env found. Generating new credentials..."
  cat > "$ENV_FILE" <<EOF
ENVIRONMENT=development
POSTGRES_DB=db_$(rand_str 10)
POSTGRES_PASSWORD=$(rand_str 16)
POSTGRES_USER=user_$(rand_str 10)
POSTGRES_HOST=db
POSTGRES_PORT=5432
DEBUG=true
SECRET_KEY=$(rand_str 32)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key_here
CLERK_SECRET_KEY=your_clerk_secret_here
RESEND_API_KEY=your_resend_api_key_here
EOF
  chmod 600 "$ENV_FILE"
fi

cd "$APP_DIR"

# === SSL CERTIFICATE SETUP ===
# Issue cert on first boot, reuse on subsequent boots
SSL_DIR="${APP_DIR}/nginx/ssl"
ACME_DIR="${APP_DIR}/acme"
PUBLIC_IP=$(hostname -I | awk '{print $1}')

echo "Droplet IP: $PUBLIC_IP"

if [ -f "${SSL_DIR}/fullchain.pem" ] && [ -f "${SSL_DIR}/privkey.pem" ]; then
  echo "SSL certs already exist, skipping issuance"
else
  echo "Issuing SSL certificate for $PUBLIC_IP..."
  mkdir -p "$SSL_DIR"

  # Issue cert (requires port 80 to be free - run before docker compose up)
  docker run --rm --net=host \
    -v "${ACME_DIR}:/acme" \
    -v "${SSL_DIR}:/ssl" \
    neilpang/acme.sh \
    acme.sh --issue --server letsencrypt --cert-profile shortlived --standalone -d "$PUBLIC_IP" --home /acme

  # Install cert (copy to nginx ssl dir)
  docker run --rm \
    -v "${ACME_DIR}:/acme" \
    -v "${SSL_DIR}:/ssl" \
    neilpang/acme.sh \
    acme.sh --install-cert -d "$PUBLIC_IP" --ecc --home /acme \
    --key-file /ssl/privkey.pem --fullchain-file /ssl/fullchain.pem

  echo "SSL certificate issued successfully"
fi

# Start services
docker compose up -d

echo "=== Startup complete: $(date -Is) ==="