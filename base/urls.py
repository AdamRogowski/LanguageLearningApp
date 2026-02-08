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
    path("my-lessons/", views.myLessons, name="my-lessons"),
    path("my-lessons/directory/<int:directory_id>/", views.myLessons, name="my-lessons-directory"),
    # Directory management
    path("create-directory/<int:directory_id>/", views.createDirectory, name="create-directory"),
    path("rename-directory/<int:directory_id>/", views.renameDirectory, name="rename-directory"),
    path("move-directory/<int:directory_id>/", views.moveDirectory, name="move-directory"),
    path("delete-directory/<int:directory_id>/", views.deleteDirectory, name="delete-directory"),
    path("move-lesson/<int:my_lesson_id>/", views.moveLesson, name="move-lesson"),
    path("drag-drop-move/", views.dragDropMove, name="drag-drop-move"),
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
        views.importAndCopyLesson,
        name="import-lesson",
    ),
    path("create-lesson/", views.createLesson, name="create-lesson"),
    path("copy_lesson/<int:my_lesson_id>/", views.copyLesson, name="copy-lesson"),
    path("edit_lesson/<int:my_lesson_id>/", views.editLesson, name="edit-lesson"),
    path("edit_word/<int:my_word_id>/", views.editWord, name="edit-word"),
    path("delete_word/<int:my_word_id>/", views.deleteWord, name="delete-word"),
    path(
        "start_practice/<int:user_lesson_id>/<str:mode>/",
        views.start_practice,
        name="start-practice",
    ),
    path("practice/<int:user_lesson_id>/<str:mode>/", views.practice, name="practice"),
    path(
        "practice_feedback/<int:user_lesson_id>/<str:mode>/",
        views.practice_feedback,
        name="practice-feedback",
    ),
    path(
        "cancel_practice/<int:user_lesson_id>/",
        views.cancel_practice,
        name="cancel-practice",
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
            template_name="base/unauthenticated/password_reset_form.html"
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="base/unauthenticated/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="base/unauthenticated/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="base/unauthenticated/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("settings/", views.settings_view, name="settings"),
    path(
        "password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="base/authenticated/user_profile/password_change_form.html", success_url="/settings/"
        ),
        name="password_change",
    ),
    path(
        "export-lesson/<int:lesson_id>/",
        views.export_lesson_json,
        name="export-lesson-json",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
