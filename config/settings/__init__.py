import os
from pathlib import Path

from dotenv import load_dotenv

# .env из корня проекта. override=True — файл важнее пустых/старых переменных окружения
load_dotenv(
    Path(__file__).resolve().parent.parent.parent / '.env',
    override=True,
)

env = os.environ.get('DJANGO_ENV', 'local')

if env == 'prod':
    from .prod import *  # noqa: F401,F403
else:
    from .local import *  # noqa: F401,F403
