#!/usr/bin/env bash
# Provisioning del VPS DigitalOcean Ubuntu 22.04+
# Correr como root tras crear droplet:
#   wget https://your-host/vps_provision.sh
#   chmod +x vps_provision.sh
#   ./vps_provision.sh
#
# O pegarlo en el campo "User Data" al crear el droplet (cloud-init).

set -euo pipefail

NEW_USER="${NEW_USER:-ambient}"
TIMEZONE="America/Santiago"

echo "═══ 1. Update sistema ═══"
apt-get update
apt-get upgrade -y

echo "═══ 2. Deps base ═══"
apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    htop \
    ufw \
    fail2ban \
    unattended-upgrades \
    ca-certificates \
    rsync \
    python3.11 \
    python3.11-venv \
    python3-pip \
    libpq-dev \
    libsndfile1 \
    ffmpeg

echo "═══ 3. Timezone ═══"
timedatectl set-timezone "$TIMEZONE"

echo "═══ 4. Crear usuario no-root ═══"
if ! id "$NEW_USER" &>/dev/null; then
    adduser --gecos "" --disabled-password "$NEW_USER"
    usermod -aG sudo "$NEW_USER"
    echo "$NEW_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$NEW_USER"
    mkdir -p "/home/$NEW_USER/.ssh"
    if [ -f /root/.ssh/authorized_keys ]; then
        cp /root/.ssh/authorized_keys "/home/$NEW_USER/.ssh/"
    fi
    chown -R "$NEW_USER:$NEW_USER" "/home/$NEW_USER/.ssh"
    chmod 700 "/home/$NEW_USER/.ssh"
    chmod 600 "/home/$NEW_USER/.ssh/authorized_keys" 2>/dev/null || true
fi

echo "═══ 5. Hardening SSH ═══"
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
systemctl restart ssh

echo "═══ 6. Firewall ═══"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable

echo "═══ 7. fail2ban ═══"
systemctl enable fail2ban
systemctl start fail2ban

echo "═══ 8. Unattended upgrades ═══"
dpkg-reconfigure -fnoninteractive unattended-upgrades

echo "═══ 9. Swap (2GB, importante para encoding en VPS 2GB RAM) ═══"
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "═══ 10. Proyecto en /opt ═══"
mkdir -p /opt/ambient_machine
chown -R "$NEW_USER:$NEW_USER" /opt/ambient_machine

cat << 'EOF'

╔════════════════════════════════════════════════════════╗
║  VPS PROVISIONING DONE                                 ║
╠════════════════════════════════════════════════════════╣
║  Próximo: desde tu Mac:                                ║
║                                                        ║
║  rsync -avz --exclude '.venv' --exclude 'data' \       ║
║    ~/projects/ambient_machine/ \                       ║
║    ambient@<VPS_IP>:/opt/ambient_machine/              ║
║                                                        ║
║  Luego SSH al VPS:                                     ║
║  ssh ambient@<VPS_IP>                                  ║
║  cd /opt/ambient_machine                               ║
║  bash setup.sh                                         ║
║                                                        ║
║  Auth del canal (requiere browser local con SSH        ║
║  tunnel para OAuth callback):                          ║
║  ssh -L 8080:localhost:8080 ambient@<VPS_IP>           ║
║  cd /opt/ambient_machine && source .venv/bin/activate  ║
║  python -m src.youtube_uploader --auth-only            ║
║                                                        ║
║  Cron (ver vps_cron.txt):                              ║
║  crontab vps_cron.txt                                  ║
╚════════════════════════════════════════════════════════╝

EOF
