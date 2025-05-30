from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("login/", views.loginPage, name="login"),
    path("logout/", views.logoutUser, name="logout"),
    path("register/", views.registerPage, name="register"),
    path("", views.home, name="home"),
    path("my-lessons/<str:pk>/", views.myLessons, name="my-lessons"),
    path(
        "delete-my-lesson/<int:my_lesson_id>/",
        views.deleteMyLesson,
        name="delete-my-lesson",
    ),
    path(
        "my-lesson-details/<int:my_lesson_id>/",
        views.myLessonDetails,
        name="my-lesson-details",
    ),
    path(
        "my-word-details/<int:my_word_id>/",
        views.myWordDetails,
        name="my-word-details",
    ),
    path("lessons-repository/", views.lessonsRepository, name="lessons-repository"),
    path(
        "lessons-repository/<int:lesson_id>/",
        views.lessonDetails,
        name="lesson-details",
    ),
    path(
        "rate-lesson/<int:lesson_id>/",
        views.rateLesson,
        name="rate-lesson",
    ),
    path(
        "lessons-repository/<int:lesson_id>/<str:prompt>/",
        views.wordDetails,
        name="word-details",
    ),
    path(
        "import-lesson/<int:lesson_id>/",
        views.importLesson,
        name="import-lesson",
    ),
    path("create-lesson/", views.createLesson, name="create-lesson"),
    path("copy_lesson/<int:my_lesson_id>/", views.copyLesson, name="copy-lesson"),
    path("edit_lesson/<int:my_lesson_id>/", views.editLesson, name="edit-lesson"),
    path("edit_word/<int:my_word_id>/", views.editWord, name="edit-word"),
    path("delete_word/<int:my_word_id>/", views.deleteWord, name="delete-word"),
    path(
        "start_practice/<int:user_lesson_id>/",
        views.start_practice,
        name="start-practice",
    ),
    path("practice/<int:user_lesson_id>/", views.practice, name="practice"),
    path(
        "cancel_practice/<int:user_lesson_id>/",
        views.cancel_practice,
        name="cancel-practice",
    ),
    path(
        "practice_feedback/<int:user_lesson_id>/",
        views.practice_feedback,
        name="practice-feedback",
    ),
    path(
        "reset_progress/<int:my_lesson_id>/", views.resetProgress, name="reset-progress"
    ),
    path("import_lesson_json/", views.import_lesson_json, name="import-lesson-json"),
    path(
        "generate_lesson_audio/<int:my_lesson_id>/start/",
        views.generate_lesson_audio_start,
        name="generate-lesson-audio-start",
    ),
    path(
        "generate_lesson_audio/<int:my_lesson_id>/",
        views.generate_lesson_audio,
        name="generate-lesson-audio",
    ),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="base/password_reset_form.html"
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="base/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="base/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="base/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("settings/", views.settings_view, name="settings"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
