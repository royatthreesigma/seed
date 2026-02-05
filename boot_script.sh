#!/usr/bin/env bash
set -euo pipefail

exec > >(tee -a /var/log/startup-script.log) 2>&1
echo "=== boot_script started: $(date -Is) ==="

# ========== Configuration ==========
DEPLOY_USER="${DEPLOY_USER:-deployer}"
MOUNT_DIR="${MOUNT_DIR:-/mnt/pr_data}"
APP_DIR="${APP_DIR:-/seed}"


# ========== Docker installation ==========
# Beucase we want the latest Ububtu (24.04) but Docker is not provided by default (at least on DigitalOcean), 
# we need to select the Ububtu version we want and install `docker` and `docker compose` ourselves
# This script is adapted from the official Docker installation instructions for Ubuntu: https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-22-04

# update your existing list of packages
sudo apt update

# install a few prerequisite packages which let apt use packages over HTTPS
# `-y` to auto-confirm prompts; some disk space will be consumed
sudo apt install ca-certificates curl gnupg -y

# add the GPG key for the official Docker repository to your system
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# add the Docker repository to APT sources:
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# update your existing list of packages again for the addition to be recognized:
sudo apt update

# make sure you are about to install from the Docker repo instead of the default Ubuntu repo:
apt-cache policy docker-ce

# install Docker
# `-y` to auto-confirm prompts; some disk space will be consumed
sudo apt install docker-ce -y

# if you want to avoid typing sudo whenever you run the docker command, add your username to the docker group
sudo usermod -aG docker ${USER}

# to apply the new group membership, log out of the server and back in, or type the following:
su - ${USER}

# if you installed Docker from the official Docker repository in Step 1, you can install the Compose v2 plugin with apt:
sudo apt update
# `-y` to auto-confirm prompts; some disk space will be consumed
sudo apt install docker-compose-plugin -y





# ========== User setup and provisioning ==========
# From user_data you call:
#   MOUNT_DIR="$MOUNT_DIR" APP_DIR="/seed" bash /seed/boot_script.sh
MOUNT_DIR="${MOUNT_DIR:-/mnt/pr_data}"
APP_DIR="${APP_DIR:-/seed}"

# Ensure the node_modules directory exists on the volume
mkdir -p "${MOUNT_DIR}/node_modules"

ENV_FILE="${ENV_FILE:-${APP_DIR}/.env}"
SSL_DIR="${SSL_DIR:-${APP_DIR}/nginx/ssl}"

# Persist acme state on the volume (so renewals work)
ACME_HOME="${ACME_HOME:-${MOUNT_DIR}/acme}"
ACME_IMAGE="${ACME_IMAGE:-neilpang/acme.sh}"

rand_str() {
  local len="${1:-16}"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$(( (len + 1) / 2 ))" | head -c "$len"
  else
    tr -dc 'a-zA-Z0-9' </dev/urandom | head -c "$len"
  fi
}

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: APP_DIR not found at $APP_DIR"
  exit 1
fi

# DigitalOcean metadata service gives the public IPv4 reliably
# curl http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address :contentReference[oaicite:3]{index=3}
PUBLIC_IP="$(curl -fsS http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || true)"
if [ -z "${PUBLIC_IP}" ]; then
  PUBLIC_IP="$(hostname -I | awk '{print $1}')"
fi
echo "Droplet public IP: ${PUBLIC_IP}"

mkdir -p "$SSL_DIR" "$ACME_HOME"

# .env: generate once; reuse on next boots
if [ -f "$ENV_FILE" ]; then
  echo "Reusing existing .env file (preserving credentials)"
  if grep -q "^NEXT_PUBLIC_API_URL=" "$ENV_FILE"; then
    sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://${PUBLIC_IP}/api|" "$ENV_FILE"
  else
    echo "NEXT_PUBLIC_API_URL=https://${PUBLIC_IP}/api" >> "$ENV_FILE"
  fi
else
  echo "No .env found. Generating new credentials..."
  cat > "$ENV_FILE" <<ENVEOF
ENVIRONMENT=development
POSTGRES_DB=db_$(rand_str 10)
POSTGRES_PASSWORD=$(rand_str 16)
POSTGRES_USER=user_$(rand_str 10)
POSTGRES_HOST=db
POSTGRES_PORT=5432
DEBUG=true
SECRET_KEY=$(rand_str 32)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key_here
NEXT_PUBLIC_API_URL=https://${PUBLIC_IP}/api
CLERK_SECRET_KEY=your_clerk_secret_here
RESEND_API_KEY=your_resend_api_key_here
ENVEOF
  chmod 600 "$ENV_FILE"
fi

cd "$APP_DIR"

# Ensure Docker is up
systemctl enable --now docker >/dev/null 2>&1 || true

# ---- SSL issuance (ONLY if missing) ----
# Let’s Encrypt IP certs are GA and are 6-day; you must select the shortlived profile. :contentReference[oaicite:4]{index=4}
# acme.sh supports: --cert-profile shortlived :contentReference[oaicite:5]{index=5}
if [ -s "${SSL_DIR}/fullchain.pem" ] && [ -s "${SSL_DIR}/privkey.pem" ]; then
  echo "SSL certs already exist; skipping issuance"
else
  echo "Issuing Let's Encrypt IP cert (shortlived) for ${PUBLIC_IP}..."
  # Important: this must run while port 80 is free. We do it BEFORE compose up.
  docker run --rm --net=host \
    -v "${ACME_HOME}:/acme.sh" \
    -v "${SSL_DIR}:/ssl" \
    "${ACME_IMAGE}" \
    sh -c "
      acme.sh --home /acme.sh --set-default-ca --server letsencrypt &&
      acme.sh --home /acme.sh --issue --standalone -d '${PUBLIC_IP}' --cert-profile shortlived --keylength ec-256 &&
      acme.sh --home /acme.sh --install-cert -d '${PUBLIC_IP}' --ecc \
        --fullchain-file /ssl/fullchain.pem \
        --key-file /ssl/privkey.pem
    "

  chmod 600 "${SSL_DIR}/privkey.pem" || true
fi

# ---- Start services ----
docker compose up -d --build

# ---- Renewal automation (twice daily) ----
# 6-day certs => renew frequently. :contentReference[oaicite:6]{index=6}
cat > /usr/local/bin/acme_renew.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

MOUNT_DIR="${MOUNT_DIR:-/mnt/pr_data}"
APP_DIR="${APP_DIR:-/seed}"
ACME_HOME="${ACME_HOME:-${MOUNT_DIR}/acme}"
ACME_IMAGE="${ACME_IMAGE:-neilpang/acme.sh}"

PUBLIC_IP="$(curl -fsS http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || true)"
[ -n "$PUBLIC_IP" ] || PUBLIC_IP="$(hostname -I | awk '{print $1}')"

cd "$APP_DIR"

# Free port 80 for standalone renew by stopping proxy briefly
docker compose stop proxy || true

docker run --rm --net=host \
  -v "${ACME_HOME}:/acme.sh" \
  -v "${APP_DIR}/nginx/ssl:/ssl" \
  "${ACME_IMAGE}" \
  sh -c "
    acme.sh --home /acme.sh --cron &&
    acme.sh --home /acme.sh --install-cert -d '${PUBLIC_IP}' --ecc \
      --fullchain-file /ssl/fullchain.pem \
      --key-file /ssl/privkey.pem
  "

docker compose up -d proxy || true
docker compose restart proxy || true
EOF
chmod +x /usr/local/bin/acme_renew.sh

cat > /etc/systemd/system/acme-renew.service <<EOF
[Unit]
Description=Renew Let’s Encrypt shortlived IP certs (acme.sh)
Wants=network-online.target
After=network-online.target docker.service

[Service]
Type=oneshot
Environment=MOUNT_DIR=${MOUNT_DIR}
Environment=APP_DIR=${APP_DIR}
Environment=ACME_HOME=${ACME_HOME}
Environment=ACME_IMAGE=${ACME_IMAGE}
ExecStart=/usr/local/bin/acme_renew.sh
EOF

cat > /etc/systemd/system/acme-renew.timer <<'EOF'
[Unit]
Description=Run acme-renew twice daily

[Timer]
OnCalendar=*-*-* 00,12:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now acme-renew.timer

echo "=== boot_script complete: $(date -Is) ==="
