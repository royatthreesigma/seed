#!/usr/bin/env bash
set -euo pipefail

exec > >(tee -a /var/log/startup-script.log) 2>&1
echo "=== boot_script started: $(date -Is) ==="

# ========== Configuration ==========
DEPLOY_USER="${DEPLOY_USER:-deployer}"
MOUNT_DIR="${MOUNT_DIR:-/mnt/pr_data}"
APP_DIR="${APP_DIR:-/seed}"

# ========== Phase 1: Root-only tasks ==========
setup_as_root() {
  echo "Running root setup tasks..."
  
  # Create deploy user if missing
  if ! id "$DEPLOY_USER" &>/dev/null; then
    echo "Creating user: $DEPLOY_USER"
    useradd -m -s /bin/bash -G sudo "$DEPLOY_USER"
    
    # Copy SSH authorized_keys from root
    deploy_home=$(getent passwd "$DEPLOY_USER" | cut -d: -f6)
    mkdir -p "${deploy_home}/.ssh"
    [ -f /root/.ssh/authorized_keys ] && cp /root/.ssh/authorized_keys "${deploy_home}/.ssh/"
    chmod 700 "${deploy_home}/.ssh"
    chmod 600 "${deploy_home}/.ssh/authorized_keys" 2>/dev/null || true
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${deploy_home}/.ssh"
    
    # Passwordless sudo for setup (remove later if desired)
    printf '%s ALL=(ALL) NOPASSWD:ALL\n' "$DEPLOY_USER" > "/etc/sudoers.d/90-${DEPLOY_USER}"
    chmod 440 "/etc/sudoers.d/90-${DEPLOY_USER}"
  fi

  # Install Docker engine
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg lsb-release

  local keyring_dir=/etc/apt/keyrings
  install -m 0755 -d "$keyring_dir"
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --batch --yes --dearmor -o "${keyring_dir}/docker.gpg"
  chmod a+r "${keyring_dir}/docker.gpg"

  printf 'deb [arch=%s signed-by=%s/docker.gpg] https://download.docker.com/linux/ubuntu %s stable\n' \
    "$(dpkg --print-architecture)" "$keyring_dir" "$(lsb_release -cs)" > /etc/apt/sources.list.d/docker.list

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

  # Add deploy user to docker group
  usermod -aG docker "$DEPLOY_USER"

  # Ensure Docker is running
  systemctl enable --now docker

  # Grant ownership of app directory to deploy user
  [ -d "$APP_DIR" ] && chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$APP_DIR"
  [ -d "$MOUNT_DIR" ] && chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$MOUNT_DIR"

  echo "Root setup complete. Re-executing as $DEPLOY_USER..."
  
  # Re-run this script as the deploy user
  exec sudo -u "$DEPLOY_USER" \
    MOUNT_DIR="$MOUNT_DIR" \
    APP_DIR="$APP_DIR" \
    DEPLOY_USER="$DEPLOY_USER" \
    bash "$0" --user-phase
}

# ========== Phase 2: Deploy user tasks ==========
setup_as_deploy_user() {
  echo "Running setup as $(whoami)..."

  mkdir -p "${MOUNT_DIR}/node_modules"

  local env_file="${APP_DIR}/.env"
  local ssl_dir="${APP_DIR}/nginx/ssl"
  local acme_home="${MOUNT_DIR}/acme"

  mkdir -p "$ssl_dir" "$acme_home"

  # Get public IP from DO metadata
  local public_ip
  public_ip=$(curl -fsS http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null) || \
    public_ip=$(hostname -I | awk '{print $1}')
  echo "Public IP: $public_ip"

  # Generate .env if missing
  if [ ! -f "$env_file" ]; then
    echo "Generating .env..."
    cat > "$env_file" <<EOF
ENVIRONMENT=development
POSTGRES_DB=db_$(openssl rand -hex 5)
POSTGRES_PASSWORD=$(openssl rand -hex 8)
POSTGRES_USER=user_$(openssl rand -hex 5)
POSTGRES_HOST=db
POSTGRES_PORT=5432
DEBUG=true
SECRET_KEY=$(openssl rand -hex 16)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key_here
NEXT_PUBLIC_API_URL=https://${public_ip}/api
CLERK_SECRET_KEY=your_clerk_secret_here
RESEND_API_KEY=your_resend_api_key_here
EOF
    chmod 600 "$env_file"
  else
    # Update API URL in existing .env
    sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://${public_ip}/api|" "$env_file"
  fi

  cd "$APP_DIR"

  # Issue SSL cert if missing
  if [ ! -s "${ssl_dir}/fullchain.pem" ] || [ ! -s "${ssl_dir}/privkey.pem" ]; then
    echo "Issuing Let's Encrypt cert for ${public_ip}..."
    docker run --rm --net=host \
      -v "${acme_home}:/acme.sh" \
      -v "${ssl_dir}:/ssl" \
      neilpang/acme.sh \
      sh -c "
        acme.sh --home /acme.sh --set-default-ca --server letsencrypt &&
        acme.sh --home /acme.sh --issue --standalone -d '${public_ip}' --cert-profile shortlived --keylength ec-256 &&
        acme.sh --home /acme.sh --install-cert -d '${public_ip}' --ecc \
          --fullchain-file /ssl/fullchain.pem \
          --key-file /ssl/privkey.pem
      "
    chmod 600 "${ssl_dir}/privkey.pem" 2>/dev/null || true
  fi

  # Start services
  docker compose up -d --build

  echo "=== boot_script complete: $(date -Is) ==="
}

# ========== Entry point ==========
if [ "${1:-}" = "--user-phase" ]; then
  setup_as_deploy_user
elif [ "$(id -u)" -eq 0 ]; then
  setup_as_root
else
  echo "ERROR: Must run as root initially"
  exit 1
fi