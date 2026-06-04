#!/bin/bash
# ShopNest — one-shot deployment script for Ubuntu/Debian VPS
# Usage: bash deploy.sh
set -e

DOMAIN="shopnest.mediaghor.com"
APP_DIR="/var/www/shopnest"
REPO="https://github.com/tanmoymondal1312/ShopNest.git"

echo "=== ShopNest Deployment ==="

# 1. System packages
apt-get update -q
apt-get install -y python3 python3-venv python3-pip nginx git curl

# 2. Clone / pull latest
if [ -d "$APP_DIR/.git" ]; then
  echo "Pulling latest code..."
  cd "$APP_DIR" && git pull
else
  echo "Cloning repository..."
  git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi

# 3. Virtual env & dependencies
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r requirements.txt

# 4. .env — create only if missing
if [ ! -f "$APP_DIR/.env" ]; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > "$APP_DIR/.env" <<EOF
ADMIN_USER=admin
ADMIN_PASS=change_this_password
SECRET_KEY=$SECRET
EOF
  echo "Created .env — CHANGE THE ADMIN PASSWORD before going live!"
fi

# 5. Seed database (safe — uses INSERT OR IGNORE)
cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" seed.py

# 6. Fix permissions
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"

# 7. Nginx config
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/shopnest
ln -sf /etc/nginx/sites-available/shopnest /etc/nginx/sites-enabled/shopnest
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 8. Systemd service
cp "$APP_DIR/deploy/shopnest.service" /etc/systemd/system/shopnest.service
systemctl daemon-reload
systemctl enable shopnest
systemctl restart shopnest

echo ""
echo "=== Done! ==="
echo "Site running at: http://$DOMAIN"
echo "Admin panel:     http://$DOMAIN/admin/login"
echo ""
echo "Next: add DNS A record in Cloudflare:"
echo "  Type: A  |  Name: shopnest  |  Value: $(curl -s ifconfig.me)"
echo "  Proxy: ON (orange cloud)"
