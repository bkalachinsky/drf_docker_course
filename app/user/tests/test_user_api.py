"""Tests for user API"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the public features of the user API"""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful"""
        content = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }
        result = self.client.post(CREATE_USER_URL, content)

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=content['email'])
        self.assertTrue(user.check_password(content['password']))
        self.assertNotIn('password', result.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with email exists"""
        content = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }
        create_user(**content)
        result = self.client.post(CREATE_USER_URL, content)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """Test that the password must be more than 5 characters"""
        content = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'Test Name',
        }
        result = self.client.post(CREATE_USER_URL, content)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=content['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test generates token for valid credentials"""
        user_details = {
            'name': 'Test Name',
            'email': 'test@example.com',
            'password': 'testpass123',
        }
        create_user(**user_details)

        content = {
            'email': user_details['email'],
            'password': user_details['password'],
        }
        result = self.client.post(TOKEN_URL, content)

        self.assertIn('token', result.data)
        self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Test returns error if credentials invalid"""
        create_user(email='test@example.com', password='goodpass')
        content = {
            'email': 'test@example.com',
            'password': 'badpass',
        }
        result = self.client.post(TOKEN_URL, content)

        self.assertNotIn('token', result.data)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Test returns error if password is blank"""
        content = {
            'email': 'test@example.com',
            'password': '',
        }
        result = self.client.post(TOKEN_URL, content)
        self.assertNotIn('token', result.data)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for users"""
        result = self.client.get(ME_URL)

        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """Test API requests that require authentication"""

    def setUp(self):
        """Setup for tests"""
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name='Test Name',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user"""
        result = self.client.get(ME_URL)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, {
            'name': self.user.name,
            'email': self.user.email,
        })

    def test_post_me_not_allowed(self):
        """Test POST is not allowed for the me endpoint"""
        result = self.client.post(ME_URL, {})

        self.assertEqual(
            result.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_user_profile(self):
        """Test updating the user profile for the authenticated user"""
        content = {
            'name': 'Updated name',
            'password': 'updatedpass123',
        }
        result = self.client.patch(ME_URL, content)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, content['name'])
        self.assertTrue(self.user.check_password(content['password']))
        self.assertEqual(result.status_code, status.HTTP_200_OK)
