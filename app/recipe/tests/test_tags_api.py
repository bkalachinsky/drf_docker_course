"""Test for the tags API"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag
from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """Create and return a tag detail URL"""
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a new user"""
    return get_user_model().objects.create_user(email, password)


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required"""
        result = self.client.get(TAGS_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags"""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Dessert")

        result = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user"""
        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name="Fruity")
        tag = Tag.objects.create(user=self.user, name="Comfort Food")

        result = self.client.get(TAGS_URL)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0]['name'], tag.name)
        self.assertEqual(result.data[0]['id'], tag.id)

    def test_update_tag(self):
        """Test updating a tag"""
        tag = Tag.objects.create(user=self.user, name="After Dinner")

        content = {'name': 'Dessert'}
        url = detail_url(tag.id)
        result = self.client.patch(url, content)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, content['name'])

    def test_delete_tag(self):
        """Test for deleting a tag"""
        tag = Tag.objects.create(user=self.user, name='Some name')

        url = detail_url(tag.id)
        result = self.client.delete(url)

        self.assertEqual(result.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())
