import os

env = os.environ.get('DJANGO_ENV', 'local')

if env == 'prod':
    from .prod import *  # noqa: F401,F403
else:
    from .local import *  # noqa: F401,F403
