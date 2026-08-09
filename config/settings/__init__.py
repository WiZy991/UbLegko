import os
from pathlib import Path

from dotenv import load_dotenv

# Загрузка .env из корня проекта (локально и на сервере)
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

env = os.environ.get('DJANGO_ENV', 'local')

if env == 'prod':
    from .prod import *  # noqa: F401,F403
else:
    from .local import *  # noqa: F401,F403
