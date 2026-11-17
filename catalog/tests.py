from django.test import TestCase
from django.urls import reverse
from .models import Show


class CatalogVisibilityTests(TestCase):
    def test_drafts_are_not_visible_in_public_catalog(self):
        Show.objects.create(title="Unpublished Show", slug="unpublished-show")
        response = self.client.get(reverse("show-list"))
        self.assertNotContains(response, "Unpublished Show")

    def test_published_show_is_visible_in_public_catalog(self):
        Show.objects.create(title="Published Show", slug="published-show", status=Show.Status.PUBLISHED)
        response = self.client.get(reverse("show-list"))
        self.assertContains(response, "Published Show")
