from django.urls import path
from . import views


urlpatterns = [
    path("login/", views.loginPage, name="login"),
    path("logout/", views.logoutUser, name="logout"),
    path("register/", views.registerPage, name="register"),
    path("", views.home, name="home"),
    path("room/<str:pk>/", views.room, name="room"),
    path("profile/<str:pk>/", views.userProfile, name="user-profile"),
    path("create-room/", views.createRoom, name="create-room"),
    path("update-room/<str:pk>/", views.updateRoom, name="update-room"),
    path("delete-room/<str:pk>/", views.deleteRoom, name="delete-room"),
    path("delete-comment/<str:pk>/", views.deleteComment, name="delete-comment"),
    path("my-lessons/<str:pk>/", views.myLessons, name="my-lessons"),
    path("lessons-repository/", views.lessonsRepository, name="lessons-repository"),
    path("lessons-repository/<str:pk>/", views.lessonDetails, name="lesson-details"),
    path(
        "lessons-repository/<str:pk>/<str:prompt>/",
        views.wordDetails,
        name="word-details",
    ),
]
