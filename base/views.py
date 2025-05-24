from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q  # Import Q for complex queries
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Room, Topic, Message, Lesson, Word, UserLesson, UserWord
from .forms import RoomForm

"""
rooms = [
    {"id": 1, "name": "Room 1"},
    {"id": 2, "name": "Room 2"},
    {"id": 3, "name": "Room 3"},
]
"""


def loginPage(request):
    page = "login"
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username").lower()
        password = request.POST.get("password")

        try:
            user = User.objects.get(username=username)
        except:
            messages.error(request, "User does not exist")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Username OR password does not exist")

    context = {"page": page}
    return render(request, "base/login_register.html", context)


def logoutUser(request):
    logout(request)
    messages.info(request, "User was logged out")
    return redirect("home")


def registerPage(request):
    page = "register"
    form = UserCreationForm()

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "An error occurred during registration")

    context = {"form": form, "page": page}
    return render(request, "base/login_register.html", context)


def home(request):
    q = request.GET.get("q") if request.GET.get("q") != None else ""
    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) | Q(name__icontains=q) | Q(description__icontains=q)
    )
    room_count = rooms.count()
    topics = Topic.objects.all()

    comments = Message.objects.filter(
        Q(room__topic__name__icontains=q)
        | Q(room__name__icontains=q)
        | Q(body__icontains=q)
    ).order_by("-created")

    user = request.user
    if user.is_authenticated:
        user = User.objects.get(id=request.user.id)
    else:
        user = None

    context = {
        "rooms": rooms,
        "topics": topics,
        "room_count": room_count,
        "comments": comments,
        "user": user,
    }
    return render(request, "base/home.html", context)


def room(request, pk):
    room = Room.objects.get(id=pk)
    comments = room.message_set.all().order_by("-created")
    participants = room.participants.all()

    if request.method == "POST":
        room.message_set.create(
            user=request.user, body=request.POST.get("body"), room=room
        )
        room.participants.add(request.user)
        return redirect("room", pk=room.id)

    context = {"room": room, "comments": comments, "participants": participants}
    return render(request, "base/room.html", context)


def userProfile(request, pk):
    user_profile = User.objects.get(id=pk)
    rooms = user_profile.room_set.all()
    comments = user_profile.message_set.all()
    topics = Topic.objects.all()

    context = {
        "user_profile": user_profile,
        "rooms": rooms,
        "comments": comments,
        "topics": topics,
    }
    return render(request, "base/profile.html", context)


@login_required(login_url="login")
def createRoom(request):
    form = RoomForm()
    if request.method == "POST":
        form = RoomForm(request.POST)

        if form.is_valid():
            room = form.save(commit=False)
            room.host = request.user
            room.save()
            return redirect("home")

    context = {"form": form}
    return render(request, "base/room_form.html", context)


@login_required(login_url="login")
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)

    if request.user != room.host and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    if request.method == "POST":
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            print("Form is valid")
            form.save()
            return redirect("home")

    context = {"form": form, "room": room}
    return render(request, "base/room_form.html", context)


@login_required(login_url="login")
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    if request.method == "POST":
        room.delete()
        return redirect("home")
    context = {"obj": room}
    return render(request, "base/delete.html", context)


@login_required(login_url="login")
def deleteComment(request, pk):
    comment = Message.objects.get(id=pk)
    # room_id = comment.room.id  # Get the room ID before deleting the comment

    if request.user != comment.user and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    if request.method == "POST":
        comment.delete()
        return redirect("home")  # Redirect to the room

    context = {"obj": comment}
    return render(request, "base/delete.html", context)


# Language learning app views.py


@login_required(login_url="login")
def myLessons(request, pk):
    user = User.objects.get(id=pk)

    if request.user.id != user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    user_lessons = UserLesson.objects.filter(user=user).order_by("-id")
    if not user_lessons:
        return HttpResponse("You do not have any lessons yet.")
    # else:
    #    return HttpResponse(
    #        f"There ae {user_lessons.count()} lessons for you. {user_lessons[0].lesson.title} is the first one."
    #    )

    context = {
        "user": user,
        "my_lessons": user_lessons,
    }
    return render(request, "base/my_lessons.html", context)


@login_required(login_url="login")
def deleteMyLesson(request, my_lesson_id):
    myLesson = UserLesson.objects.filter(id=my_lesson_id).first()
    if not myLesson:
        return HttpResponse("You do not have this lesson.")

    if request.user.id != myLesson.user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    if request.method == "POST":
        # Delete all UserWord instances related to this UserLesson
        UserWord.objects.filter(
            user=myLesson.user, word__lesson=myLesson.lesson
        ).delete()
        # Then delete the UserLesson instance
        myLesson.delete()
        messages.success(request, "Your lesson was deleted successfully.")
        return redirect("my-lessons", pk=request.user.id)

    context = {
        "my_lesson": myLesson,
        "my_words": UserWord.objects.filter(
            user=myLesson.user, word__lesson=myLesson.lesson
        ).order_by("-id"),
    }
    return render(request, "base/delete_my_lesson.html", context)


@login_required(login_url="login")
def myLessonDetails(request, my_lesson_id):

    myLesson = UserLesson.objects.filter(id=my_lesson_id).first()
    if not myLesson:
        return HttpResponse("You do not have this lesson.")

    if request.user.id != myLesson.user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    myWords = UserWord.objects.filter(
        user=myLesson.user, word__lesson=myLesson.lesson
    ).order_by("-id")

    context = {
        "my_lesson": myLesson,
        "my_words": myWords,
    }
    return render(request, "base/my_lesson_details.html", context)


@login_required(login_url="login")
def myWordDetails(request, my_word_id):

    myWord = UserWord.objects.filter(id=my_word_id).first()
    if not myWord:
        return HttpResponse("You do not have this word in your lesson.")

    if request.user.id != myWord.user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    myLesson = UserLesson.objects.filter(
        user=myWord.user, lesson=myWord.word.lesson
    ).first()

    context = {
        "my_lesson": myLesson,
        "my_word": myWord,
    }
    return render(request, "base/my_word_details.html", context)


def lessonsRepository(request):

    # This view will display the lessons repository
    public_lessons = Lesson.objects.all().filter(is_public=True).order_by("-id")

    context = {
        "public_lessons": public_lessons,
    }
    return render(request, "base/lessons_repository.html", context)


def lessonDetails(request, lesson_id):

    # This view will display the lesson overview
    lesson = Lesson.objects.get(id=lesson_id)
    if not lesson:
        return HttpResponse("Lesson not found")
    if not lesson.is_public:
        return HttpResponse("This lesson is not public")
    words = lesson.words.all()

    context = {
        "lesson": lesson,
        "words": words,
    }
    return render(request, "base/lesson_details.html", context)


def wordDetails(request, lesson_id, prompt):

    # This view will display the word details
    lesson = Lesson.objects.get(id=lesson_id)
    if not lesson.is_public:
        return HttpResponse("This lesson is not public")
    words = lesson.words.all()
    word = Word.objects.get(prompt=prompt, lesson=lesson)
    if not word:
        return HttpResponse("Word not found")

    context = {
        "lesson": lesson,
        "word": word,
    }
    return render(request, "base/word_details.html", context)


@login_required(login_url="login")
def importLesson(request, lesson_id):
    try:
        lesson = Lesson.objects.get(id=lesson_id)
        user = request.user

        if UserLesson.objects.filter(user=user, lesson=lesson).exists():
            return HttpResponse("You have already imported this lesson.")

        UserLesson.objects.create(user=user, lesson=lesson, target_progress=0)

        words = Word.objects.filter(lesson=lesson)
        for word in words:
            UserWord.objects.create(user=user, word=word, current_progress=0, notes="")

        return redirect("my-lessons", pk=user.id)
    except Exception as e:
        return HttpResponse(f"Error: {e}")
