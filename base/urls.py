from django.urls import path
from . import views


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
]
