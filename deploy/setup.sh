#!/usr/bin/env bash
# Установка UbLegko на Ubuntu 24.04 (Timeweb / VPS).
# Запуск от root:
#   bash setup.sh YOUR_SERVER_IP [GITHUB_REPO_URL]
set -euo pipefail

SERVER_IP="${1:-}"
REPO_URL="${2:-https://github.com/WiZy991/UbLegko.git}"
APP_DIR="/var/www/ublegko"

if [[ -z "$SERVER_IP" ]]; then
  echo "Использование: bash setup.sh YOUR_SERVER_IP [REPO_URL]"
  echo "Пример: bash setup.sh 1.2.3.4"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запустите скрипт от root: sudo bash setup.sh ..."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip git nginx curl

mkdir -p /var/www
if [[ -d "$APP_DIR/.git" ]]; then
  echo ">> Обновляю репозиторий..."
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" reset --hard origin/main
else
  echo ">> Клонирую $REPO_URL ..."
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [[ ! -f .env ]]; then
  SECRET="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(50))')"
  cat > .env <<EOF
DJANGO_ENV=prod
DJANGO_SECRET_KEY=${SECRET}
ALLOWED_HOSTS=${SERVER_IP},localhost,127.0.0.1
SESSION_COOKIE_SECURE=0
CSRF_COOKIE_SECURE=0

# ВАЖНО: без SMTP заявки сохраняются, но на почту НЕ приходят!
# Раскомментируйте и заполните (см. deploy/env.example):
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.mail.ru
# EMAIL_PORT=587
# EMAIL_USE_TLS=1
# EMAIL_USE_SSL=0
# EMAIL_HOST_USER=your-mailbox@mail.ru
# EMAIL_HOST_PASSWORD=your-smtp-password
# DEFAULT_FROM_EMAIL=your-mailbox@mail.ru
# ORDER_EMAIL_TO=pro-brite_uss@mail.ru
EOF
  echo ">> Создан файл .env (настройте SMTP, иначе письма заявок не уходят!)"
else
  echo ">> .env уже есть — не перезаписываю"
fi

# Подхват переменных для manage.py
set -a
# shellcheck disable=SC1091
source "$APP_DIR/.env"
set +a

mkdir -p media staticfiles
chown -R www-data:www-data "$APP_DIR"
chmod -R u+rwX,g+rwX "$APP_DIR"

run_django() {
  sudo -u www-data bash -c "set -a; source '$APP_DIR/.env'; set +a; cd '$APP_DIR'; .venv/bin/python manage.py $*"
}

run_django migrate --noinput
run_django collectstatic --noinput
run_django seed_cities || true

cp "$APP_DIR/deploy/gunicorn.service" /etc/systemd/system/ublegko.service
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/ublegko
ln -sfn /etc/nginx/sites-available/ublegko /etc/nginx/sites-enabled/ublegko
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl daemon-reload
systemctl enable ublegko
systemctl restart ublegko
systemctl restart nginx

ufw allow OpenSSH || true
ufw allow 'Nginx Full' || true
ufw --force enable || true

echo
echo "============================================"
echo " Установка завершена"
echo " Сайт: http://${SERVER_IP}/"
echo " Админка: http://${SERVER_IP}/admin/"
echo
echo " Создайте суперпользователя:"
echo "   cd ${APP_DIR}"
echo "   sudo -u www-data bash -c 'set -a; source .env; set +a; .venv/bin/python manage.py createsuperuser'"
echo
echo " Если есть локальная БД с товарами — скопируйте db.sqlite3 и media/,"
echo " затем: systemctl restart ublegko"
echo "============================================"
