from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q  # Import Q for complex queries
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Room, Topic, Message
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

    context = {
        "rooms": rooms,
        "topics": topics,
        "room_count": room_count,
        "comments": comments,
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
