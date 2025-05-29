from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q  # Import Q for complex queries
from django.db.models import Avg  # Import Avg for aggregation
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Lesson, Word, UserLesson, UserWord, AccessType, Rating, Language
from .forms import RateLessonForm, UserLessonForm, UserWordForm
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
    my_Words_search_query = request.GET.get("q") or ""

    if my_Words_search_query:
        myWords = myWords.filter(
            Q(word__prompt__icontains=my_Words_search_query)
            | Q(word__translation__icontains=my_Words_search_query)
            | Q(word__usage__icontains=my_Words_search_query)
            | Q(word__hint__icontains=my_Words_search_query)
            | Q(notes__icontains=my_Words_search_query)
        ).order_by("id")

    is_author = myLesson.lesson.author == request.user

    is_private = myLesson.lesson.access_type.name == "private"
    if request.user == myLesson.lesson.author or myLesson.lesson.access_type.name in [
        "write"
    ]:
        can_edit = True
    else:
        can_edit = False

    userWordForm = UserWordForm()

    if can_edit:

        if request.method == "POST":
            userWordForm = UserWordForm(request.POST)
            if userWordForm.is_valid():
                # Extract word data from the form
                word_data = userWordForm.cleaned_data.get("word")
                prompt = (
                    word_data.prompt
                    if word_data
                    else userWordForm.cleaned_data.get("prompt")
                )
                translation = (
                    word_data.translation
                    if word_data
                    else userWordForm.cleaned_data.get("translation")
                )
                usage = (
                    word_data.usage
                    if word_data
                    else userWordForm.cleaned_data.get("usage")
                )
                hint = (
                    word_data.hint
                    if word_data
                    else userWordForm.cleaned_data.get("hint")
                )

                # Check if the word already exists in the lesson
                if Word.objects.filter(prompt=prompt, lesson=myLesson.lesson).exists():
                    messages.error(request, "This word already exists in the lesson.")
                    return redirect("my-lesson-details", my_lesson_id=myLesson.id)

                # Create the Word instance and associate with the lesson
                new_word = Word(
                    prompt=prompt,
                    translation=translation,
                    usage=usage,
                    hint=hint,
                    lesson=myLesson.lesson,
                )
                new_word.save()

                # Now create the UserWord instance with the new Word
                UserWord.objects.create(
                    user_lesson=myLesson,
                    word=new_word,
                    current_progress=0,
                    notes=userWordForm.cleaned_data.get("notes", ""),
                )

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
        "word_form": userWordForm,
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

    # Use UserWordForm, passing the UserWord instance and the related Word instance for initial values
    if request.method == "POST":
        edit_word_form = UserWordForm(
            request.POST, instance=myWord, word_instance=myWord.word
        )
        if edit_word_form.is_valid():
            # Update Word fields
            myWord.word.prompt = edit_word_form.cleaned_data["prompt"]
            myWord.word.translation = edit_word_form.cleaned_data["translation"]
            myWord.word.usage = edit_word_form.cleaned_data["usage"]
            myWord.word.hint = edit_word_form.cleaned_data["hint"]
            myWord.word.save()
            # Update UserWord notes
            myWord.notes = edit_word_form.cleaned_data["notes"]
            myWord.save()

            # Update the lesson's updated time to reflect changes
            myWord.user_lesson.lesson.updated = timezone.now()
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
    else:
        edit_word_form = UserWordForm(instance=myWord, word_instance=myWord.word)

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


@login_required
def start_practice(request, user_lesson_id):
    window_key = f"practice_{user_lesson_id}_window"
    pool_key = f"practice_{user_lesson_id}_pool"
    # Ensure only one session per user per lesson by clearing any existing session data
    request.session.pop(window_key, None)
    request.session.pop(pool_key, None)

    user_lesson = get_object_or_404(UserLesson, id=user_lesson_id, user=request.user)
    user_words = list(
        UserWord.objects.filter(
            user_lesson=user_lesson, current_progress__lt=user_lesson.target_progress
        ).values_list("id", flat=True)
    )
    shuffle(user_words)
    window = user_words[: user_lesson.practice_window]
    pool = user_words[user_lesson.practice_window :]
    request.session[window_key] = window
    request.session[pool_key] = pool
    return redirect("practice", user_lesson_id=user_lesson_id)


@login_required
def practice(request, user_lesson_id):
    window_key = f"practice_{user_lesson_id}_window"
    pool_key = f"practice_{user_lesson_id}_pool"
    answer_key = f"practice_{user_lesson_id}_answer"
    window = request.session.get(window_key, [])
    pool = request.session.get(pool_key, [])

    if not window:
        # Session complete
        request.session.pop(window_key, None)
        request.session.pop(pool_key, None)
        request.session.pop(answer_key, None)
        messages.info(request, "Practice session completed!")
        return redirect("my-lesson-details", my_lesson_id=user_lesson_id)

    user_word = get_object_or_404(
        UserWord,
        id=window[0],
        user_lesson__user=request.user,
        user_lesson_id=user_lesson_id,
    )

    if request.method == "POST":
        answer = request.POST.get("answer", "").strip()
        correct = answer.lower() == user_word.word.prompt.lower()
        # Store answer and correctness in session
        request.session[answer_key] = {
            "user_word_id": user_word.id,
            "answer": answer,
            "correct": correct,
            "correct_answer": user_word.word.prompt,
        }
        return redirect("practice-feedback", user_lesson_id=user_lesson_id)

    return render(
        request,
        "base/practice.html",
        {"user_word": user_word, "user_lesson_id": user_lesson_id},
    )


@login_required
def practice_feedback(request, user_lesson_id):
    window_key = f"practice_{user_lesson_id}_window"
    pool_key = f"practice_{user_lesson_id}_pool"
    answer_key = f"practice_{user_lesson_id}_answer"
    window = request.session.get(window_key, [])
    pool = request.session.get(pool_key, [])
    answer_data = request.session.get(answer_key)

    if not answer_data or not window:
        return redirect("practice", user_lesson_id=user_lesson_id)

    user_word = get_object_or_404(
        UserWord,
        id=answer_data["user_word_id"],
        user_lesson__user=request.user,
        user_lesson_id=user_lesson_id,
    )

    if request.method == "POST":
        # Accept as correct or continue
        if answer_data["correct"] or "accept_as_correct" in request.POST:
            user_word.current_progress += 1
            user_word.save()
            window.pop(0)
            if pool:
                window.append(pool.pop(0))
        else:
            user_word.current_progress = max(0, user_word.current_progress - 1)
            user_word.save()
            word_id = window.pop(0)
            window.append(word_id)
        # Save updated session state
        request.session[window_key] = window
        request.session[pool_key] = pool
        request.session.pop(answer_key, None)
        return redirect("practice", user_lesson_id=user_lesson_id)

    context = {
        "user_word": user_word,
        "user_lesson_id": user_lesson_id,
        "answer": answer_data["answer"],
        "correct": answer_data["correct"],
        "correct_answer": answer_data["correct_answer"],
    }
    return render(request, "base/practice_feedback.html", context)


@login_required
def cancel_practice(request, user_lesson_id):
    window_key = f"practice_{user_lesson_id}_window"
    pool_key = f"practice_{user_lesson_id}_pool"
    request.session.pop(window_key, None)
    request.session.pop(pool_key, None)
    messages.info(request, "Practice session cancelled.")
    return redirect("my-lesson-details", my_lesson_id=user_lesson_id)
