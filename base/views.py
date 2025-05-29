from django.db import transaction
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q  # Import Q for complex queries
from django.db.models import Avg  # Import Avg for aggregation
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Lesson, Word, UserLesson, UserWord, AccessType, Rating, Language
from .forms import WordForm, RateLessonForm, UserLessonForm
from django.utils import timezone
from random import shuffle


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


@login_required(login_url="login")
def myLessons(request, pk):
    user = User.objects.get(id=pk)

    if request.user.id != user.id and request.user.is_superuser == False:
        return HttpResponse("You are not allowed here!")

    user_lessons = UserLesson.objects.filter(user=user).order_by("-id")
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

    # --- Ensure all words in the lesson have a corresponding UserWord for this UserLesson ---
    lesson_words = myLesson.lesson.words.all()
    existing_userword_word_ids = set(
        UserWord.objects.filter(user_lesson=myLesson).values_list("word_id", flat=True)
    )
    missing_words = [w for w in lesson_words if w.id not in existing_userword_word_ids]
    for word in missing_words:
        UserWord.objects.create(
            user_lesson=myLesson, word=word, current_progress=0, notes=""
        )
    # ----------------------------------------------------------------------

    myWords = UserWord.objects.filter(user_lesson=myLesson).order_by("-id")

    is_author = myLesson.lesson.author == request.user

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
                myLesson.lesson.changes_log = (
                    (
                        myLesson.lesson.changes_log + "\n"
                        if myLesson.lesson.changes_log
                        else ""
                    )
                    + f"{timezone.now()} Word '{new_word.prompt}' added by {request.user.username}"
                )
                myLesson.lesson.save()  # Save the lesson to update the timestamp
                messages.success(request, "Word created successfully!")
                return redirect("my-lesson-details", my_lesson_id=myLesson.id)

    context = {
        "my_lesson": myLesson,
        "my_words": myWords,
        "word_form": wordForm,
        "can_edit": can_edit,
        "is_private": is_private,
        "is_author": is_author,
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

    lessonRatings = Rating.objects.filter(lesson=lesson)
    rating_count = lessonRatings.count()
    average_rating = (
        round(lessonRatings.aggregate(Avg("rating"))["rating__avg"], 1)
        if lessonRatings.exists()
        else 0.0
    )

    # rated_already = Rating.objects.filter(user=user, lesson=lesson).first()

    words = lesson.words.all()

    context = {
        "lesson": lesson,
        "words": words,
        "can_import": can_import,
        "average_rating": average_rating,
        "rating_count": rating_count,
    }
    return render(request, "base/lesson_details.html", context)


@login_required(login_url="login")
def rateLesson(request, lesson_id):

    rateLessonForm = RateLessonForm()

    # This view will handle the rating of a lesson
    if request.method == "POST":
        lesson = Lesson.objects.get(id=lesson_id)
        if not lesson:
            return HttpResponse("Lesson not found")

        user = request.user
        if not user.is_authenticated:
            return HttpResponse("You must be logged in to rate a lesson.")

        form = RateLessonForm(request.POST)
        if form.is_valid():
            rating_value = form.cleaned_data["rating"]

            # Check if the user has already rated this lesson
            existing_rating = Rating.objects.filter(user=user, lesson=lesson).first()
            if existing_rating:
                existing_rating.rating = rating_value
                existing_rating.save()

                lesson.changes_log = (
                    (lesson.changes_log + "\n" if lesson.changes_log else "")
                    + f"{timezone.now()} Rating updated by {user.username} to {rating_value}"
                )
                messages.success(request, "Your rating has been updated.")
            else:
                Rating.objects.create(user=user, lesson=lesson, rating=rating_value)
                lesson.changes_log = (
                    lesson.changes_log + "\n" if lesson.changes_log else ""
                ) + f"{timezone.now()} Rated by {user.username} with {rating_value}"

                messages.success(request, "Thank you for your rating!")
            lesson.save()
            return redirect("lesson-details", lesson_id=lesson_id)
        else:
            messages.error(request, "Invalid rating form submission.")

    context = {
        "rate_lesson_form": rateLessonForm,
        "lesson": Lesson.objects.get(id=lesson_id),
    }
    return render(request, "base/rate_lesson.html", context)


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
        lesson.changes_log = (
            lesson.changes_log + "\n" if lesson.changes_log else ""
        ) + f"{timezone.now()} Lesson imported by {user.username}"
        lesson.save()

        return redirect("my-lessons", pk=user.id)
    except Exception as e:
        return HttpResponse(f"Error: {e}")


@login_required(login_url="login")
@transaction.atomic  # ensures rollback on failure
def createLesson(request):

    if request.method == "POST":
        user_lesson_form = UserLessonForm(request.POST)

        if user_lesson_form.is_valid():
            # First, create and save the Lesson instance from form data
            lesson = Lesson(
                title=user_lesson_form.cleaned_data["title"],
                description=user_lesson_form.cleaned_data["description"],
                prompt_language=user_lesson_form.cleaned_data["prompt_language"],
                translation_language=user_lesson_form.cleaned_data[
                    "translation_language"
                ],
                access_type=user_lesson_form.cleaned_data["access_type"],
                author=request.user,
            )
            lesson.changes_log = (
                lesson.changes_log + "\n" if lesson.changes_log else ""
            ) + f"{timezone.now()} Lesson created by {request.user.username}"
            lesson.save()

            # Now create the UserLesson and assign the lesson
            myLesson = user_lesson_form.save(commit=False)
            myLesson.lesson = lesson
            myLesson.user = request.user
            myLesson.save()

            messages.success(request, "Lesson created successfully!")
            return redirect("my-lesson-details", my_lesson_id=myLesson.id)
    else:
        user_lesson_form = UserLessonForm()

    context = {"lesson_form": user_lesson_form}
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
    lesson.changes_log = (
        lesson.changes_log + "\n" if lesson.changes_log else ""
    ) + f"{timezone.now()} Lesson copied by {request.user.username}"

    new_lesson = Lesson(
        title=lesson.title,
        description=lesson.description,
        prompt_language=lesson.prompt_language,
        translation_language=lesson.translation_language,
        author=request.user,
        access_type=AccessType.objects.get(name="private"),  # Set to private by default
        original_lesson=lesson,  # Link to the original lesson
        changes_log=lesson.changes_log,
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
        request.user
        == myLesson.lesson.author
        # or myLesson.lesson.access_type.name in ["write"]
    ):
        return HttpResponse("You do not have rights to edit this lesson!")

    lesson_instance = myLesson.lesson

    # Use UserLessonForm, passing lesson_instance for initial lesson fields
    edit_user_lesson_form = UserLessonForm(
        instance=myLesson, lesson_instance=lesson_instance
    )

    # Store original values for comparison
    original_data = {
        "title": lesson_instance.title,
        "description": lesson_instance.description,
        "prompt_language": lesson_instance.prompt_language,
        "translation_language": lesson_instance.translation_language,
        "access_type": lesson_instance.access_type,
        "target_progress": myLesson.target_progress,
        "practice_window": myLesson.practice_window,
    }

    if request.method == "POST":
        edit_user_lesson_form = UserLessonForm(
            request.POST, instance=myLesson, lesson_instance=lesson_instance
        )
        if edit_user_lesson_form.is_valid():
            # Update UserLesson fields
            myLesson = edit_user_lesson_form.save(commit=False)
            # Update related Lesson fields from form data
            lesson_instance.title = edit_user_lesson_form.cleaned_data["title"]
            lesson_instance.description = edit_user_lesson_form.cleaned_data[
                "description"
            ]
            lesson_instance.prompt_language = edit_user_lesson_form.cleaned_data[
                "prompt_language"
            ]
            lesson_instance.translation_language = edit_user_lesson_form.cleaned_data[
                "translation_language"
            ]
            lesson_instance.access_type = edit_user_lesson_form.cleaned_data[
                "access_type"
            ]

            # Compare fields and build a diff string
            changes = []
            for field, old_value in original_data.items():
                if field in [
                    "title",
                    "description",
                    "prompt_language",
                    "translation_language",
                    "access_type",
                ]:
                    new_value = getattr(lesson_instance, field)
                else:
                    new_value = getattr(myLesson, field)
                # For related fields, compare their pk or str
                if hasattr(old_value, "pk"):
                    old_val = old_value.pk if old_value else None
                    new_val = new_value.pk if new_value else None
                else:
                    old_val = old_value
                    new_val = new_value
                if old_val != new_val:
                    changes.append(f"{field}: '{old_value}' → '{new_value}'")

            # lesson_instance.save()
            myLesson.save()

            # Update the lesson's updated time to reflect changes
            lesson_instance.updated = timezone.now()

            # Build the change log entry
            if changes:
                diff_str = "; ".join(changes)
                log_entry = f"{timezone.now()} Lesson edited by {request.user.username}: {diff_str}"
            else:
                log_entry = f"{timezone.now()} Lesson edited by {request.user.username}: No changes detected"

            lesson_instance.changes_log = (
                lesson_instance.changes_log + "\n"
                if lesson_instance.changes_log
                else ""
            ) + log_entry
            lesson_instance.save()
            messages.success(request, "Lesson updated successfully!")
            return redirect("my-lesson-details", my_lesson_id=myLesson.id)

    context = {
        "edit_user_lesson_form": edit_user_lesson_form,
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
            myWord.user_lesson.lesson.changes_log = (
                (
                    myWord.user_lesson.lesson.changes_log + "\n"
                    if myWord.user_lesson.lesson.changes_log
                    else ""
                )
                + f"{timezone.now()} Word '{myWord.word.prompt}' edited by {request.user.username}"
            )
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
    wordNameToDelete = myWord.word.prompt

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
        myLesson.lesson.changes_log = (
            myLesson.lesson.changes_log + "\n" if myLesson.lesson.changes_log else ""
        ) + f"{timezone.now()} Word '{wordNameToDelete}' deleted by {user.username}"
        myLesson.lesson.save()
        return redirect("my-lesson-details", my_lesson_id=myLesson.id)

    context = {
        "my_word": myWord,
    }

    return render(request, "base/delete_word.html", context)


# ------------Practice Views------------#
