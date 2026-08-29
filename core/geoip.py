"""Определение страны/региона/города по IP (без внешних зависимостей)."""

from __future__ import annotations

import ipaddress
import json
import logging
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)


def _is_public_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def lookup_ip_geo(ip: str | None) -> dict[str, str]:
    """Возвращает geo_country, geo_region, geo_city для публичного IP."""
    if not ip or not _is_public_ip(ip):
        return {}

    try:
        url = (
            f'http://ip-api.com/json/{ip}'
            '?fields=status,country,regionName,city&lang=ru'
        )
        with urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError):
        logger.debug('Не удалось определить гео для IP %s', ip, exc_info=True)
        return {}

    if data.get('status') != 'success':
        return {}

    return {
        'geo_country': (data.get('country') or '')[:80],
        'geo_region': (data.get('regionName') or '')[:120],
        'geo_city': (data.get('city') or '')[:120],
    }
