from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.utils import timezone
from datetime import timedelta

from analytics.stats import count_online_now
from core.analytics import touch_site_presence
from core.models import SitePresence


def _browser_request(user):
    request = RequestFactory().get(
        '/',
        HTTP_USER_AGENT='Mozilla/5.0 (compatible; ublegko-test)',
    )
    SessionMiddleware(lambda req: None).process_request(request)
    request.session.save()
    request.user = user
    return request


class OnlinePresenceTests(TestCase):
    def test_same_account_on_phone_and_computer_counts_as_two(self):
        user = get_user_model().objects.create_user('visitor', password='secret')
        touch_site_presence(_browser_request(user))
        touch_site_presence(_browser_request(user))
        self.assertEqual(count_online_now(), 2)

    def test_same_browser_stays_one(self):
        user = get_user_model().objects.create_user('solo', password='secret')
        request = _browser_request(user)
        touch_site_presence(request)
        touch_site_presence(request)
        self.assertEqual(count_online_now(), 1)

    def test_closed_page_drops_out(self):
        SitePresence.objects.create(
            presence_key='s:old',
            last_seen_at=timezone.now() - timedelta(seconds=10),
        )
        self.assertEqual(count_online_now(), 0)
