#!/usr/bin/env bash
# Восстановление UbLegko на новом VPS:
# 1) GitHub (код) через deploy/setup.sh
# 2) данные из /root/ublegko-data.tar (.env, db.sqlite3, media)
set -euo pipefail

SERVER_IP="${1:-82.202.130.23}"
DATA_TAR="${2:-/root/ublegko-data.tar}"
APP_DIR="/var/www/ublegko"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запустите от root"
  exit 1
fi

if [[ ! -f "$DATA_TAR" ]]; then
  echo "Нет файла данных: $DATA_TAR"
  echo "Сначала залейте: scp ublegko-data.tar root@${SERVER_IP}:/root/"
  exit 1
fi

echo ">> Ставлю/обновляю код с GitHub..."
if [[ -f /var/www/ublegko/deploy/setup.sh ]]; then
  bash /var/www/ublegko/deploy/setup.sh "$SERVER_IP"
else
  curl -fsSL -o /tmp/setup_ublegko.sh \
    https://raw.githubusercontent.com/WiZy991/UbLegko/main/deploy/setup.sh
  bash /tmp/setup_ublegko.sh "$SERVER_IP"
fi

echo ">> Останавливаю сайт, восстанавливаю БД/фото/.env..."
systemctl stop ublegko || true

if [[ -f "$APP_DIR/.env" ]]; then
  cp -a "$APP_DIR/.env" "$APP_DIR/.env.before-restore"
fi

tar -xf "$DATA_TAR" -C "$APP_DIR" .env db.sqlite3 media

chown -R www-data:www-data "$APP_DIR"
chmod -R u+rwX,g+rwX "$APP_DIR"

sudo -u www-data bash -c "set -a; source '$APP_DIR/.env'; set +a; cd '$APP_DIR'; .venv/bin/python manage.py migrate --noinput"
sudo -u www-data bash -c "set -a; source '$APP_DIR/.env'; set +a; cd '$APP_DIR'; .venv/bin/python manage.py collectstatic --noinput"

systemctl restart ublegko
systemctl restart nginx

echo
echo "============================================"
echo " Готово"
echo " Сайт по IP: http://${SERVER_IP}/"
echo " Админка:    http://${SERVER_IP}/admin/"
echo
echo " Домен ублегко.рф: направь A-запись на ${SERVER_IP},"
echo " затем: certbot --nginx -d xn--90aefvcv3a.xn--p1ai -d www.xn--90aefvcv3a.xn--p1ai"
echo "============================================"
