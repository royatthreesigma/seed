#cloud-config
runcmd:
    - |
    bash -lc 
    # ========== USER SETUP ==========
    # Setup the Ubuntu24.04 droplet with a non-root sudo user, and then run the rest of the provisioning as that user
    USERNAME={user_name} # TODO: Customize the sudo non-root username here

    # Create user and immediately expire password to force a change on login
    useradd --create-home --shell &#34;/bin/bash&#34; --groups sudo &#34;${USERNAME}&#34;
    passwd --delete &#34;${USERNAME}&#34;
    chage --lastday 0 &#34;${USERNAME}&#34;

    # Create SSH directory for sudo user and move keys over
    home_directory=&#34;$(eval echo ~${USERNAME})&#34;
    mkdir --parents &#34;${home_directory}/.ssh&#34;
    cp /root/.ssh/authorized_keys &#34;${home_directory}/.ssh&#34;
    chmod 0700 &#34;${home_directory}/.ssh&#34;
    chmod 0600 &#34;${home_directory}/.ssh/authorized_keys&#34;
    chown --recursive &#34;${USERNAME}&#34;:&#34;${USERNAME}&#34; &#34;${home_directory}/.ssh&#34;

    # Disable root SSH login with password
    sed --in-place &#39;s/^PermitRootLogin.*/PermitRootLogin prohibit-password/g&#39; /etc/ssh/sshd_config
    if sshd -t -q; then systemctl restart sshd fi


    # ========== PROVISIONING ==========
    set -euo pipefail
    echo "=== cloud-init runcmd started: $(date -Is) ==="

    VOLUME_NAME="{vol_name}"
    """+"""
    REPO_URL="https://github.com/royatthreesigma/seed.git"

    # Mount the volume here (conventional mount point)
    MOUNT_DIR="/mnt/pr_data"

    # We will CLONE INTO THIS PATH on the mounted volume:
    APP_DIR="${MOUNT_DIR}/seed"

    # Persisted data dirs on the mounted volume
    DB_DIR="${MOUNT_DIR}/db-data"
    NODEMOD_DIR="${MOUNT_DIR}/node_modules"

    # Firewall
    ufw allow OpenSSH >/dev/null 2>&1 || true
    ufw allow 80/tcp  >/dev/null 2>&1 || true
    ufw allow 443/tcp >/dev/null 2>&1 || true
    ufw --force enable >/dev/null 2>&1 || true

    # DO recommends mounting volumes via /dev/disk/by-id because /dev/sdX can change.
    DEV="/dev/disk/by-id/scsi-0DO_Volume_${VOLUME_NAME}"

    # Wait for device to appear
    for i in $(seq 1 90); do
    [ -e "$DEV" ] && break
    sleep 1
    done
    if [ ! -e "$DEV" ]; then
    echo "ERROR: Volume device not found: $DEV"
    ls -la /dev/disk/by-id || true
    exit 1
    fi

    mkdir -p "$MOUNT_DIR"

    # Format only if needed
    if ! blkid "$DEV" >/dev/null 2>&1; then
    echo "No filesystem detected on $DEV; formatting ext4..."
    mkfs.ext4 -F "$DEV"
    fi

    # DO mount options + fstab persistence (defaults,nofail,discard,noatime).
    if ! grep -q "^${DEV} " /etc/fstab; then
    echo "${DEV} ${MOUNT_DIR} ext4 defaults,nofail,discard,noatime 0 2" >> /etc/fstab
    fi

    mount -a
    findmnt "$MOUNT_DIR" >/dev/null || (echo "ERROR: mount failed" && exit 1)

    # Persisted dirs for your compose binds - create them directly on volume
    mkdir -p "$DB_DIR" "$NODEMOD_DIR"

    # Clone repo ONTO THE VOLUME at /mnt/pr_data/seed, and symlink /seed -> that
    if [ ! -d "${APP_DIR}/.git" ]; then
    echo "Cloning repo into $APP_DIR..."
    git clone "$REPO_URL" "$APP_DIR"
    else
    echo "Repo already exists at $APP_DIR; keeping local changes"
    fi

    # ========== Launch the app ==========
    ln -sfn "$APP_DIR" /seed

    chmod +x /seed/boot_script.sh
    MOUNT_DIR="$MOUNT_DIR" APP_DIR="/seed" bash /seed/boot_script.sh

    echo "=== cloud-init runcmd complete: $(date -Is) ==="