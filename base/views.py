from django.forms import modelform_factory
from django.forms import formset_factory, CharField, Form
from django.db import transaction
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q  # Import Q for complex queries
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Room, Topic, Message, Lesson, Word, UserLesson, UserWord, AccessType
from .forms import RoomForm, LessonForm, WordForm
from django.utils import timezone

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
        username = request.POST.get("username")
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

    user = request.user
    if user.is_authenticated:
        user = User.objects.get(id=request.user.id)
    else:
        user = None

    context = {
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
    # if not user_lessons:
    #    return HttpResponse("You do not have any lessons yet.")
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
def myLessonDetails(request, my_lesson_id):

    myLesson = UserLesson.objects.filter(id=my_lesson_id).first()
    if not myLesson:
        return HttpResponse("You do not have this lesson.")

    if request.user.id != myLesson.user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    myWords = UserWord.objects.filter(user_lesson=myLesson).order_by("-id")

    is_private = myLesson.lesson.access_type.name == "private"
    if request.user == myLesson.lesson.author or myLesson.lesson.access_type.name in [
        "write"
    ]:
        can_edit = True
    else:
        can_edit = False

    wordForm = WordForm()

    if can_edit:

        if request.method == "POST":
            wordForm = WordForm(request.POST)
            if wordForm.is_valid():
                new_word = wordForm.save(commit=False)
                # Check if the word already exists in the lesson
                if Word.objects.filter(
                    prompt=new_word.prompt, lesson=myLesson.lesson
                ).exists():
                    messages.error(request, "This word already exists in the lesson.")
                    return redirect("my-lesson-details", my_lesson_id=myLesson.id)

                new_word.lesson = myLesson.lesson  # Associate with the lesson
                new_word.save()
                # Create a UserWord instance for the user lesson
                user_word = UserWord()
                user_word.word = new_word  # Associate the word
                user_word.current_progress = 0  # Default progress
                user_word.notes = ""  # Default notes
                user_word.user_lesson = myLesson  # Associate with the user lesson
                user_word.save()
                myLesson.lesson.updated = (
                    new_word.updated
                )  # Update lesson's updated time
                myLesson.lesson.save()  # Save the lesson to update the timestamp
                messages.success(request, "Word created successfully!")
                return redirect("my-lesson-details", my_lesson_id=myLesson.id)

    context = {
        "my_lesson": myLesson,
        "my_words": myWords,
        "word_form": wordForm,
        "can_edit": can_edit,
        "is_private": is_private,
    }
    return render(request, "base/my_lesson_details.html", context)


@login_required(login_url="login")
def deleteMyLesson(request, my_lesson_id):
    myLesson = (
        UserLesson.objects.filter(id=my_lesson_id).select_related("lesson").first()
    )
    if not myLesson:
        return HttpResponse("You do not have this lesson.")

    user = request.user
    lesson = myLesson.lesson
    is_author = hasattr(lesson, "author") and lesson.author == user
    is_private = lesson.access_type.name == "private"

    # Only the owner of the myLesson or superuser can delete
    if user.id != myLesson.user.id and not user.is_superuser:
        return HttpResponse("You are not allowed here!")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete_both":
            # Delete lesson from repository and all related UserLesson
            lesson.delete()
            messages.success(
                request,
                "Lesson and all your references were deleted from the repository.",
            )
            return redirect("my-lessons", pk=user.id)
        elif action == "delete_mylesson":
            myLesson.delete()
            messages.success(
                request,
                "Your lesson reference was deleted. The lesson remains in the repository.",
            )
            return redirect("my-lessons", pk=user.id)

    context = {
        "my_lesson": myLesson,
        "is_author": is_author,
        "is_private": is_private,
    }
    return render(request, "base/delete_my_lesson.html", context)


@login_required(login_url="login")
def myWordDetails(request, my_word_id):

    myWord = UserWord.objects.filter(id=my_word_id).first()
    if not myWord:
        return HttpResponse("You do not have this word in your lesson.")

    if (
        request.user.id != myWord.user_lesson.user.id
        and request.user.is_superuser == False
    ):
        return HttpResponse("You are not allowed here!")

    context = {
        "my_word": myWord,
    }
    return render(request, "base/my_word_details.html", context)


def lessonsRepository(request):

    # This view will display the lessons repository
    public_lessons = Lesson.objects.filter(
        access_type__name__in=["readonly", "write"]
    ).order_by("-id")

    lesson_search_query = request.GET.get("q") if request.GET.get("q") != None else ""
    public_lessons = public_lessons.filter(
        Q(title__icontains=lesson_search_query)
        | Q(description__icontains=lesson_search_query)
        | Q(prompt_language__name__icontains=lesson_search_query)
        | Q(translation_language__name__icontains=lesson_search_query)
    ).order_by("-created")

    context = {
        "public_lessons": public_lessons,
    }
    return render(request, "base/lessons_repository.html", context)


def lessonDetails(request, lesson_id):

    # This view will display the lesson overview
    lesson = Lesson.objects.get(id=lesson_id)
    if not lesson:
        return HttpResponse("Lesson not found")
    if lesson.access_type.name == "private":
        return HttpResponse("This lesson is not public")

    user = request.user
    if user.is_authenticated:
        can_import = not UserLesson.objects.filter(user=user, lesson=lesson).exists()
    else:
        can_import = False

    if lesson.access_type.name == "private":
        return HttpResponse("This lesson is private and cannot be imported.")

    words = lesson.words.all()

    context = {
        "lesson": lesson,
        "words": words,
        "can_import": can_import,
    }
    return render(request, "base/lesson_details.html", context)


def wordDetails(request, lesson_id, prompt):

    # This view will display the word details
    lesson = Lesson.objects.get(id=lesson_id)
    if lesson.access_type.name == "private":
        return HttpResponse("This lesson is not public")
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

        if lesson.access_type.name == "private":
            return HttpResponse("This lesson is private and cannot be imported.")

        newLesson = UserLesson.objects.create(
            user=user, lesson=lesson, target_progress=0
        )

        words = Word.objects.filter(lesson=lesson)
        for word in words:
            UserWord.objects.create(
                user_lesson=newLesson, word=word, current_progress=0, notes=""
            )

        return redirect("my-lessons", pk=user.id)
    except Exception as e:
        return HttpResponse(f"Error: {e}")


# ------------------------------------Create lesson view-------------------------------------


# Simple Word Input Form
# class WordInputForm(Form):
#    prompt = CharField(label="Prompt", max_length=100)
#    translation = CharField(label="Translation", max_length=100)


# WordFormSet = formset_factory(WordInputForm, extra=3)


@login_required(login_url="login")
@transaction.atomic  # ensures rollback on failure
def createLesson(request):

    if request.method == "POST":
        lesson_form = LessonForm(request.POST)

        if lesson_form.is_valid():
            # Save lesson and associate it with the user
            lesson = lesson_form.save(commit=False)
            lesson.author = request.user
            lesson.save()

            # Create user's personal reference
            myLesson = UserLesson.objects.create(user=request.user, lesson=lesson)

            messages.success(request, "Lesson created successfully!")
            return redirect("my-lesson-details", my_lesson_id=myLesson.id)
    else:
        lesson_form = LessonForm()

    context = {"lesson_form": lesson_form}
    return render(request, "base/create_lesson.html", context)


@login_required(login_url="login")
@transaction.atomic
def copyLesson(request, my_lesson_id):

    myLesson = UserLesson.objects.filter(id=my_lesson_id).first()
    if not myLesson:
        return HttpResponse("You do not have this lesson.")

    if request.user.id != myLesson.user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    # Check if the lesson is private
    if myLesson.lesson.access_type.name == "private":
        return HttpResponse("You cannot copy a private lesson.")

    # Create a new lesson based on the existing one
    lesson = myLesson.lesson
    new_lesson = Lesson(
        title=lesson.title,
        description=lesson.description,
        prompt_language=lesson.prompt_language,
        translation_language=lesson.translation_language,
        author=request.user,
        access_type=AccessType.objects.get(name="private"),  # Set to private by default
        original_lesson=lesson,  # Link to the original lesson
    )
    new_lesson.save()
    # Create a UserLesson for the new lesson
    new_user_lesson = UserLesson.objects.create(user=request.user, lesson=new_lesson)

    # Copy words from the original lesson to the new lesson
    words = lesson.words.all()
    for word in words:
        new_word = Word(
            lesson=new_lesson,
            prompt=word.prompt,
            translation=word.translation,
            usage=word.usage,
            hint=word.hint,
        )
        new_word.save()
        # Create a UserWord for the new UserLesson
        UserWord.objects.create(
            user_lesson=new_user_lesson,
            word=new_word,
            current_progress=0,  # Default progress
            notes="",  # Default notes
        )
    # Remove the original lesson from the UserLesson
    myLesson.delete()

    messages.success(request, "Lesson copied successfully!")

    return redirect("my-lesson-details", my_lesson_id=new_user_lesson.id)


@login_required(login_url="login")
@transaction.atomic
def editLesson(request, my_lesson_id):

    myLesson = UserLesson.objects.filter(id=my_lesson_id).first()

    if not myLesson:
        return HttpResponse("You do not have this lesson.")

    if request.user.id != myLesson.user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    if not (
        request.user == myLesson.lesson.author
        or myLesson.lesson.access_type.name in ["write"]
    ):
        return HttpResponse("You do not have rights to edit this lesson!")

    edit_lesson_form = LessonForm(instance=myLesson.lesson)

    if request.method == "POST":
        edit_lesson_form = LessonForm(request.POST, instance=myLesson.lesson)
        if edit_lesson_form.is_valid():
            edit_lesson_form.save()
            messages.success(request, "Lesson updated successfully!")
            return redirect("my-lesson-details", my_lesson_id=myLesson.id)

    context = {
        "edit_lesson_form": edit_lesson_form,
        "my_lesson": myLesson,
    }
    return render(request, "base/edit_lesson.html", context)


@login_required(login_url="login")
@transaction.atomic
def editWord(request, my_word_id):

    myWord = UserWord.objects.filter(id=my_word_id).first()

    if not myWord:
        return HttpResponse("You do not have this word in your lesson.")

    if (
        request.user.id != myWord.user_lesson.user.id
        and request.user.is_superuser == False
    ):
        return HttpResponse("You are not allowed here!")

    if not (
        request.user == myWord.user_lesson.lesson.author
        or myWord.user_lesson.lesson.access_type.name in ["write"]
    ):
        return HttpResponse("You do not have rights to edit this lesson!")

    edit_word_form = WordForm(instance=myWord.word)

    if request.method == "POST":
        edit_word_form = WordForm(request.POST, instance=myWord.word)
        if edit_word_form.is_valid():
            edit_word_form.save()

            # Update the lesson's updated time to reflect changes
            myWord.user_lesson.lesson.updated = edit_word_form.instance.updated
            myWord.user_lesson.lesson.save()

            messages.success(request, "Lesson updated successfully!")
            return redirect("my-lesson-details", my_lesson_id=myWord.user_lesson.id)

    context = {
        "edit_word_form": edit_word_form,
        "my_word": myWord,
    }
    return render(request, "base/edit_word.html", context)


@login_required(login_url="login")
@transaction.atomic
def deleteWord(request, my_word_id):

    myWord = UserWord.objects.filter(id=my_word_id).first()
    user = request.user

    if not myWord:
        return HttpResponse("You do not have this word in your lesson.")

    myLesson = myWord.user_lesson

    if user.id != myWord.user_lesson.user.id and user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    if not (
        user == myWord.user_lesson.lesson.author
        or myWord.user_lesson.lesson.access_type.name in ["write"]
    ):
        return HttpResponse("You do not have rights to edit this lesson!")

    if request.method == "POST":

        # Delete word from repository and all related UserWord
        myWord.word.delete()
        messages.success(
            request,
            f"Word and all your references were deleted from {myLesson.lesson.title}.",
        )

        # Update the lesson's updated time to reflect changes
        myLesson.lesson.updated = timezone.now()
        myLesson.lesson.save()
        return redirect("my-lesson-details", my_lesson_id=myLesson.id)

    context = {
        "my_word": myWord,
    }

    return render(request, "base/delete_word.html", context)
