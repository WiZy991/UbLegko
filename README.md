# Убираемся Легко — сайт-каталог

Современный адаптивный каталог профессиональных моющих средств на Django + SQLite.

## Возможности

- Каталог товаров с категориями, поиском и сортировкой
- Карточка товара и рекомендации «с этим обычно берут» (фасовки линейки + комплекты)
- Корзина и оформление заявки (письмо на email заказчика)
- Избранное для авторизованных пользователей
- Регистрация, вход, личный кабинет с историей заявок
- Админка: товары, категории, статусы, изображения, заявки, пользователи
- Массовый импорт товаров из CSV/XLSX
- Страницы 404/500, адаптив от 320px

## Соответствие ТЗ

| Требование | Статус |
|---|---|
| Каталог, страница товара, поиск | Реализовано |
| Рекомендации к товару | Реализовано (блок на товаре и в корзине) |
| Корзина и оформление заявки | Реализовано (гости и авторизованные) |
| Избранное (для зарегистрированных) | Реализовано |
| Регистрация, авторизация, личный кабинет | Реализовано |
| Контакты | Реализовано |
| Письмо заявки на email заказчика | Реализовано (нужен SMTP на сервере) |
| Админка: товары, категории, статусы, фото, заявки, пользователи | Реализовано (Jazzmin) |
| Массовый импорт Excel/CSV | Реализовано |
| Русский интерфейс | Реализовано |
| Адаптив от 320×568 | Реализовано (fluid-ширина) |
| 404 / 500 | Реализовано |
| SQLite, Django, без внешних SaaS | Реализовано |
| Безопасность (админ, хеш паролей, CSRF) | Стандартные механизмы Django |

Нюансы (не блокируют сдачу): одно фото на товар; ширина fluid, а не фиксированный контейнер; рекомендации — блок, не отдельный URL меню.

## Быстрый старт

```bash
python -m venv .venv
# Windows (если Activate.ps1 блокируется политикой — не активируйте venv, вызывайте python из .venv):
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py runserver

# Альтернатива активации в PowerShell:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# .\.venv\Scripts\Activate.ps1

# Linux:
# source .venv/bin/activate
# pip install -r requirements.txt
# python manage.py migrate
# python manage.py seed_demo
# python manage.py createsuperuser
# python manage.py runserver
```

Откройте: http://127.0.0.1:8000/  
Админка: http://127.0.0.1:8000/admin/  
Тема админки: **django-jazzmin** (тёмный интерфейс, иконки, боковое меню, поиск).

## Структура

- `catalog` — категории, товары, рекомендации, поиск
- `cart` — корзина (сессия), избранное, заявки
- `accounts` — регистрация / вход / кабинет
- `core` — контакты, настройки сайта, ошибки
- `templates`, `static`, `media`

## Импорт товаров

В админке: **Товары → Импорт CSV/XLSX**.

Обязательные колонки: `name`/`Наименование товара`, `price`/`Цена`.  
Также поддерживаются: `Описание товара`, `Ед. изм.`, `Страна-производитель`, `Код товара`, `Штрихкод`, `Старая цена`.

Форматы: `.xls`, `.xlsx`, `.csv`.

После импорта каталога постройте рекомендации (фасовки + комплекты):

```bash
.venv\Scripts\python.exe manage.py seed_recommendations
```

В админке у товара можно вручную задать блок **«Рекомендуем к этому товару»** — связи показываются в обе стороны.

## Email заявок

По умолчанию письма выводятся в консоль (`EMAIL_BACKEND=console`).

Для продакшена задайте переменные окружения:

```bash
DJANGO_ENV=prod
DJANGO_SECRET_KEY=сгенерируйте-длинный-случайный-ключ
ALLOWED_HOSTS=your-domain.ru,www.your-domain.ru
# При HTTPS (по умолчанию уже 1). Если HTTP без SSL — выставьте 0:
# SESSION_COOKIE_SECURE=1
# CSRF_COOKIE_SECURE=1
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.beget.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=noreply@your-domain.ru
ORDER_EMAIL_TO=pro-brite_uss@mail.ru
```

Email для заявок также можно изменить в админке: **Настройки сайта**.

Ошибка SMTP пишется в лог; заявка в БД сохраняется в любом случае.

## Деплой на VPS (Ubuntu 24.04, Timeweb и аналоги)

Готовые файлы в папке [`deploy/`](deploy/): Nginx, systemd (Gunicorn), пример `.env`, скрипт `setup.sh`.

### 1. Создайте сервер

- ОС: **Ubuntu 24.04**
- Рекомендуемый минимум: **1 CPU / 2 GB RAM / 15 GB NVMe** (как у вас)
- Обязательно: **публичный IPv4**
- Доступ: пароль root **или** SSH-ключ

### 2. Подключитесь по SSH (с вашего ПК)

```bash
ssh root@ВАШ_IP
```

### 3. Установите сайт одной командой

```bash
curl -fsSL https://raw.githubusercontent.com/WiZy991/UbLegko/main/deploy/setup.sh -o setup.sh
bash setup.sh ВАШ_IP
```

Или вручную:

```bash
apt update && apt install -y git
git clone https://github.com/WiZy991/UbLegko.git /var/www/ublegko
cd /var/www/ublegko
bash deploy/setup.sh ВАШ_IP
```

Скрипт поставит Python, Nginx, Gunicorn, клонирует репозиторий, сделает migrate/collectstatic и запустит сервисы.

### 4. Создайте админа

```bash
cd /var/www/ublegko
sudo -u www-data bash -c 'set -a; source .env; set +a; .venv/bin/python manage.py createsuperuser'
```

Сайт: `http://ВАШ_IP/`  
Админка: `http://ВАШ_IP/admin/`

### 5. Перенос вашей локальной базы и фото (если нужно)

С ПК (PowerShell), подставьте IP:

```powershell
scp db.sqlite3 root@ВАШ_IP:/var/www/ublegko/db.sqlite3
scp -r media root@ВАШ_IP:/var/www/ublegko/
```

На сервере:

```bash
chown -R www-data:www-data /var/www/ublegko/db.sqlite3 /var/www/ublegko/media
systemctl restart ublegko
```

### 6. Домен и HTTPS (когда появится домен)

1. В DNS домена укажите A-запись на IP сервера.
2. В `/var/www/ublegko/.env` добавьте домен в `ALLOWED_HOSTS`, выставьте `SESSION_COOKIE_SECURE=1`, `CSRF_COOKIE_SECURE=1`, `CSRF_TRUSTED_ORIGINS=https://домен.ru`.
3. В Nginx замените `server_name _;` на ваш домен.
4. Установите сертификат:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d ваш-домен.ru -d www.ваш-домен.ru
systemctl restart ublegko nginx
```

### Полезные команды на сервере

```bash
systemctl status ublegko
systemctl restart ublegko
journalctl -u ublegko -f
nginx -t && systemctl reload nginx
```

### Обновление кода с GitHub

```bash
cd /var/www/ublegko
git pull
.venv/bin/pip install -r requirements.txt
sudo -u www-data bash -c 'set -a; source .env; set +a; .venv/bin/python manage.py migrate --noinput'
sudo -u www-data bash -c 'set -a; source .env; set +a; .venv/bin/python manage.py collectstatic --noinput'
systemctl restart ublegko
```

## Email заявок

Чеклист артефактов:

1. **Исходный код** — весь репозиторий проекта (без `.venv/`).
2. **База SQLite** — файл `db.sqlite3` с актуальными товарами/настройками.
3. **Медиа** — каталог `media/` (изображения товаров).
4. **Доступ к админке** — учётка суперпользователя (`createsuperuser`) + URL `/admin/`.
5. **Инструкция** — этот README (локальный запуск, Beget, email, импорт).
6. **Исключительные права** — оформляются договором, не кодом.

## Контакты магазина (по умолчанию)

- ООО СОЛНЕЧНЫЙ МЕЧ
- г. Уссурийск, ул. Горького 91, ст4
- тел. 8-991-496-18-97
- e-mail: pro-brite_uss@mail.ru
