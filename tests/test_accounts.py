import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="romario",
        email="romario@example.com",
        password="SenhaSegura@2026",
        first_name="Romário",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="SenhaSegura@2026",
        role=User.Role.ADMIN,
    )


def authenticate(client, user):
    client.force_authenticate(user=user)


@pytest.mark.django_db
def test_register_creates_only_regular_user(api_client):
    response = api_client.post(
        reverse("register"),
        {
            "username": "novo.usuario",
            "email": "novo@example.com",
            "first_name": "Novo",
            "last_name": "Usuário",
            "password": "SenhaSegura@2026",
            "password_confirmation": "SenhaSegura@2026",
            "role": User.Role.ADMIN,
        },
        format="json",
    )

    assert response.status_code == 201
    created_user = User.objects.get(username="novo.usuario")
    assert created_user.role == User.Role.USER
    assert created_user.check_password("SenhaSegura@2026")
    assert "password" not in response.data


@pytest.mark.django_db
def test_register_rejects_different_passwords(api_client):
    response = api_client.post(
        reverse("register"),
        {
            "username": "novo.usuario",
            "email": "novo@example.com",
            "password": "SenhaSegura@2026",
            "password_confirmation": "OutraSenha@2026",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "password_confirmation" in response.data


@pytest.mark.django_db
def test_token_authentication_returns_access_and_refresh(api_client, user):
    response = api_client.post(
        reverse("token-obtain-pair"),
        {"username": user.username, "password": "SenhaSegura@2026"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["access"]
    assert response.data["refresh"]


@pytest.mark.django_db
def test_current_user_requires_authentication(api_client):
    response = api_client.get(reverse("current-user"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_current_user_returns_profile_without_password(api_client, user):
    authenticate(api_client, user)

    response = api_client.get(reverse("current-user"))

    assert response.status_code == 200
    assert response.data["email"] == user.email
    assert response.data["role"] == User.Role.USER
    assert "password" not in response.data


@pytest.mark.django_db
def test_user_can_update_own_profile_but_not_role(api_client, user):
    authenticate(api_client, user)

    response = api_client.patch(
        reverse("current-user"),
        {"first_name": "Romário D.", "role": User.Role.ADMIN},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Romário D."
    assert user.role == User.Role.USER


@pytest.mark.django_db
def test_regular_user_cannot_list_users(api_client, user):
    authenticate(api_client, user)

    response = api_client.get(reverse("user-list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_list_users(api_client, admin_user, user):
    authenticate(api_client, admin_user)

    response = api_client.get(reverse("user-list"))

    assert response.status_code == 200
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_admin_can_promote_user_to_technician(api_client, admin_user, user):
    authenticate(api_client, admin_user)

    response = api_client.patch(
        reverse("user-access-update", kwargs={"pk": user.pk}),
        {"role": User.Role.TECHNICIAN},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.role == User.Role.TECHNICIAN


@pytest.mark.django_db
def test_admin_cannot_change_own_access(api_client, admin_user):
    authenticate(api_client, admin_user)

    response = api_client.patch(
        reverse("user-access-update", kwargs={"pk": admin_user.pk}),
        {"is_active": False},
        format="json",
    )

    assert response.status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.is_active is True
