# set DJANGO_SETTINGS_MODULE=languagelearningapp.settings
# pytest languagelearningapp/base/test_views.py
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import Client
from django.contrib.messages import get_messages
from .models import Lesson, Word, UserLesson, UserWord, AccessType, Language


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="testadmin", password="testadminpass", email="admin@example.com"
    )


@pytest.fixture
def access_type_private(db):
    return AccessType.objects.create(name="private")


@pytest.fixture
def access_type_write(db):
    return AccessType.objects.create(name="write")


@pytest.fixture
def access_type_readonly(db):
    return AccessType.objects.create(name="readonly")


@pytest.fixture
def language(db):
    return Language.objects.create(name="English")


@pytest.fixture
def lesson(db, user, access_type_write, language):
    return Lesson.objects.create(
        title="Test Lesson",
        description="desc",
        prompt_language=language,
        translation_language=language,
        author=user,
        access_type=access_type_write,
    )


@pytest.fixture
def user_lesson(db, user, lesson):
    return UserLesson.objects.create(user=user, lesson=lesson)


@pytest.fixture
def word(db, lesson):
    return Word.objects.create(
        lesson=lesson, prompt="hello", translation="hola", usage="usage", hint="hint"
    )


@pytest.fixture
def user_word(db, user_lesson, word):
    return UserWord.objects.create(
        user_lesson=user_lesson, word=word, current_progress=0, notes=""
    )


import pytest


@pytest.mark.django_db
def test_login_page_get(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_page_post_invalid_user(client):
    response = client.post(
        reverse("login"), {"username": "nouser", "password": "nopass"}
    )
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert any(
        "User does not exist" in str(m)
        or "Username OR password does not exist" in str(m)
        for m in messages
    )


@pytest.mark.django_db
def test_register_page_get(client):
    response = client.get(reverse("register"))
    assert response.status_code == 200
    assert "base/login_register.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_register_page_post(client):
    data = {
        "username": "newuser",
        "password1": "complexpassword123",
        "password2": "complexpassword123",
    }
    response = client.post(reverse("register"), data)
    assert response.status_code == 302  # Redirect on success


@pytest.mark.django_db
def test_home_authenticated(client, user):
    client.login(username="testuser", password="testpass")
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "base/home.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_home_unauthenticated(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "base/home.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_my_lessons_access(client, user, user_lesson):
    client.login(username="testuser", password="testpass")
    response = client.get(reverse("my-lessons", kwargs={"pk": user.id}))
    assert response.status_code == 200
    assert "base/my_lessons.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_my_lessons_forbidden(client, user, superuser, user_lesson):
    User.objects.create_user(username="other", password="pass")
    client.login(username="other", password="pass")
    response = client.get(reverse("my-lessons", kwargs={"pk": user.id}))
    assert response.status_code == 200
    assert b"You are not allowed here!" in response.content


@pytest.mark.django_db
def test_my_lesson_details_access(client, user, user_lesson):
    client.login(username="testuser", password="testpass")
    response = client.get(
        reverse("my-lesson-details", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert response.status_code == 200
    assert "base/my_lesson_details.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_my_lesson_details_forbidden(client, user, user_lesson):
    User.objects.create_user(username="other", password="pass")
    client.login(username="other", password="pass")
    response = client.get(
        reverse("my-lesson-details", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert b"You are not allowed here!" in response.content


@pytest.mark.django_db
def test_delete_my_lesson_get(client, user, user_lesson):
    client.login(username="testuser", password="testpass")
    response = client.get(
        reverse("delete-my-lesson", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert response.status_code == 200
    assert "base/delete_my_lesson.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_delete_my_lesson_post_delete_mylesson(client, user, user_lesson):
    client.login(username="testuser", password="testpass")
    response = client.post(
        reverse("delete-my-lesson", kwargs={"my_lesson_id": user_lesson.id}),
        {"action": "delete_mylesson"},
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_lessons_repository(client, lesson, access_type_write):
    response = client.get(reverse("lessons-repository"))
    assert response.status_code == 200
    assert "base/lessons_repository.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_lesson_details_public(client, lesson, user, access_type_private, language):
    response = client.get(reverse("lesson-details", kwargs={"lesson_id": lesson.id}))
    assert response.status_code == 200
    assert "base/lesson_details.html" in [t.name for t in response.templates]
    private_lesson = Lesson.objects.create(
        title="Private",
        description="desc",
        prompt_language=language,
        translation_language=language,
        author=user,
        access_type=access_type_private,
    )
    response = client.get(
        reverse("lesson-details", kwargs={"lesson_id": private_lesson.id})
    )
    assert b"This lesson is not public" in response.content


@pytest.mark.django_db
def test_import_lesson(client, user, lesson):
    client.login(username="testuser", password="testpass")
    response = client.post(reverse("import-lesson", kwargs={"lesson_id": lesson.id}))
    assert response.status_code in (302, 200)


@pytest.mark.django_db
def test_create_lesson_get(client, user):
    client.login(username="testuser", password="testpass")
    response = client.get(reverse("create-lesson"))
    assert response.status_code == 200
    assert "base/create_lesson.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_create_lesson_post(client, user, access_type_write, language):
    client.login(username="testuser", password="testpass")
    data = {
        "title": "New Lesson",
        "description": "desc",
        "prompt_language": language.id,
        "translation_language": language.id,
        "access_type": access_type_write.id,
    }
    response = client.post(reverse("create-lesson"), data)
    assert response.status_code == 200


@pytest.mark.django_db
def test_edit_lesson_get(client, user, user_lesson):
    client.login(username="testuser", password="testpass")
    response = client.get(
        reverse("edit-lesson", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert response.status_code == 200
    assert "base/edit_lesson.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_edit_lesson_post(client, user, user_lesson, access_type_write, language):
    client.login(username="testuser", password="testpass")
    data = {
        "title": "Edited Lesson",
        "description": "desc",
        "prompt_language": language.id,
        "translation_language": language.id,
        "access_type": access_type_write.id,
    }
    response = client.post(
        reverse("edit-lesson", kwargs={"my_lesson_id": user_lesson.id}), data
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_edit_word_get(client, user, user_word):
    client.login(username="testuser", password="testpass")
    response = client.get(reverse("edit-word", kwargs={"my_word_id": user_word.id}))
    assert response.status_code == 200
    assert "base/edit_word.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_edit_word_post(client, user, user_word):
    client.login(username="testuser", password="testpass")
    data = {
        "prompt": "edited",
        "translation": "editado",
        "usage": "usage",
        "hint": "hint",
    }
    response = client.post(
        reverse("edit-word", kwargs={"my_word_id": user_word.id}), data
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_delete_word_get(client, user, user_word):
    client.login(username="testuser", password="testpass")
    response = client.get(reverse("delete-word", kwargs={"my_word_id": user_word.id}))
    assert response.status_code == 200
    assert "base/delete_word.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_delete_word_post(client, user, user_word):
    client.login(username="testuser", password="testpass")
    response = client.post(reverse("delete-word", kwargs={"my_word_id": user_word.id}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_profile_view_authenticated(client, user):
    client.login(username="testuser", password="testpass")
    response = client.get(reverse("profile"))
    assert response.status_code == 200
    assert "base/profile.html" in [t.name for t in response.templates]
    assert b"memory_usage_mb" in response.content or b"MB" in response.content


@pytest.mark.django_db
def test_settings_view_get(client, user):
    client.login(username="testuser", password="testpass")
    response = client.get(reverse("settings"))
    assert response.status_code == 200
    assert "base/settings.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_settings_view_post(client, user):
    client.login(username="testuser", password="testpass")
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "display_name": "Johnny",
        "preferred_language": "English",
        "receive_notifications": True,
    }
    response = client.post(reverse("settings"), data)
    assert response.status_code == 302  # Redirect to profile


@pytest.mark.django_db
def test_export_lesson_json(client, user, lesson):
    client.login(username="testuser", password="testpass")
    response = client.get(
        reverse("export-lesson-json", kwargs={"lesson_id": lesson.id})
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert b"title" in response.content


@pytest.mark.django_db
def test_import_lesson_json_post(client, user):
    client.login(username="testuser", password="testpass")
    # Ensure the needed AccessType exists
    from .models import AccessType

    AccessType.objects.get_or_create(name="write")
    json_data = {
        "title": "Imported Lesson",
        "description": "desc",
        "prompt_language": "English",
        "translation_language": "English",
        "access_type": "write",
        "words": [
            {"prompt": "hello", "translation": "hola", "usage": "usage", "hint": "hint"}
        ],
    }
    import io
    import json as pyjson

    file = io.BytesIO()
    file.write(pyjson.dumps(json_data).encode())
    file.seek(0)
    file.name = "test.json"
    response = client.post(reverse("import-lesson-json"), {"json_file": file})
    assert response.status_code == 302  # Redirect on success


@pytest.mark.django_db
def test_generate_lesson_audio_start(client, user, user_lesson):
    client.login(username="testuser", password="testpass")
    response = client.get(
        reverse("generate-lesson-audio-start", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert response.status_code == 200
    assert "base/generate_lesson_audio.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reset_progress_post(client, user, user_lesson, user_word):
    client.login(username="testuser", password="testpass")
    response = client.post(
        reverse("reset-progress", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert response.status_code == 302  # Redirect after reset


@pytest.mark.django_db
def test_cancel_practice(client, user, user_lesson):
    client.login(username="testuser", password="testpass")
    response = client.post(
        reverse("cancel-practice", kwargs={"user_lesson_id": user_lesson.id})
    )
    assert response.status_code == 302
    assert (
        reverse("my-lesson-details", kwargs={"my_lesson_id": user_lesson.id})
        in response.url
    )


@pytest.mark.django_db
def test_my_lessons_access_denied(client, user, superuser, user_lesson):
    other = User.objects.create_user(username="other", password="pass")
    client.login(username="other", password="pass")
    response = client.get(reverse("my-lessons", kwargs={"pk": user.id}))
    assert b"You are not allowed here!" in response.content


@pytest.mark.django_db
def test_my_lesson_details_access_denied(client, user, user_lesson):
    other = User.objects.create_user(username="other", password="pass")
    client.login(username="other", password="pass")
    response = client.get(
        reverse("my-lesson-details", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert b"You are not allowed here!" in response.content


@pytest.mark.django_db
def test_edit_word_forbidden(client, user, user_word):
    other = User.objects.create_user(username="other", password="pass")
    client.login(username="other", password="pass")
    response = client.get(reverse("edit-word", kwargs={"my_word_id": user_word.id}))
    assert b"You are not allowed here!" in response.content


@pytest.mark.django_db
def test_delete_word_forbidden(client, user, user_word):
    other = User.objects.create_user(username="other", password="pass")
    client.login(username="other", password="pass")
    response = client.post(reverse("delete-word", kwargs={"my_word_id": user_word.id}))
    assert b"You are not allowed here!" in response.content


@pytest.mark.django_db
def test_export_lesson_json_forbidden(client, user, lesson):
    other = User.objects.create_user(username="other", password="pass")
    client.login(username="other", password="pass")
    response = client.get(
        reverse("export-lesson-json", kwargs={"lesson_id": lesson.id})
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_view_unauthenticated(client):
    response = client.get(reverse("profile"))
    assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
def test_settings_view_unauthenticated(client):
    response = client.get(reverse("settings"))
    assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
def test_generate_lesson_audio_unauthenticated(client, user_lesson):
    response = client.post(
        reverse("generate-lesson-audio", kwargs={"my_lesson_id": user_lesson.id})
    )
    assert response.status_code == 302  # Redirect to login
