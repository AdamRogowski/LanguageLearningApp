"""Lesson management views: CRUD operations, import/export, and repository."""
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Avg
from django.db.models.functions import Lower
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
import os

from ..models import (
    Lesson, Word, UserLesson, UserWord, AccessType, Rating, Language, UserDirectory, UserProfile
)
from ..forms import RateLessonForm, UserLessonForm, MoveLessonForm
from ..utils_tts import generate_audio_file


@login_required(login_url="login")
def home(request):
    """Redirect authenticated users to My Lessons."""
    return redirect("my-lessons")


@login_required(login_url="login")
def myLessons(request, directory_id=None):
    """Display user's lessons organized by directory."""
    user = request.user

    # Get or create root directory for the user
    root_directory = UserDirectory.get_or_create_root_directory(user)

    # Determine current directory
    if directory_id:
        current_directory = get_object_or_404(UserDirectory, id=directory_id, user=user)
    else:
        current_directory = root_directory

    # Get subdirectories in current directory
    subdirectories = UserDirectory.objects.filter(
        user=user, parent_directory=current_directory
    ).order_by(Lower("name"))

    # Get lessons in current directory
    user_lessons = UserLesson.objects.filter(
        user=user, directory=current_directory
    ).select_related(
        "lesson", "lesson__prompt_language", "lesson__translation_language"
    ).order_by(Lower("lesson__title"))

    # Get lessons without a directory (for migration purposes, put them in root)
    orphan_lessons = UserLesson.objects.filter(
        user=user, directory__isnull=True
    )
    if orphan_lessons.exists() and current_directory == root_directory:
        # Move orphan lessons to root directory
        orphan_lessons.update(directory=root_directory)
        # Refresh the query
        user_lessons = UserLesson.objects.filter(
            user=user, directory=current_directory
        ).select_related(
            "lesson", "lesson__prompt_language", "lesson__translation_language"
        ).order_by(Lower("lesson__title"))

    # Build breadcrumb path
    breadcrumb_path = current_directory.get_path()

    # Store current directory in session for use in other views
    request.session['current_directory_id'] = current_directory.id

    # Form for creating new directory
    from ..forms import UserDirectoryForm
    directory_form = UserDirectoryForm(user=user, parent_directory=current_directory)

    context = {
        "user": user,
        "my_lessons": user_lessons,
        "subdirectories": subdirectories,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "root_directory": root_directory,
        "directory_form": directory_form,
    }
    return render(request, "base/authenticated/my_lessons/my_lessons.html", context)


@login_required(login_url="login")
def myLessonDetails(request, my_lesson_id):
    """Display details of a specific user lesson."""
    myLesson = UserLesson.objects.select_related(
        "lesson", "lesson__author", "lesson__access_type", 
        "lesson__prompt_language", "lesson__translation_language"
    ).filter(id=my_lesson_id).first()
    if not myLesson:
        return HttpResponse("You do not have this lesson.", status=404)

    if request.user.id != myLesson.user.id and not request.user.is_superuser:
        return HttpResponse("You are not allowed here!", status=403)

    # Ensure all words in the lesson have a corresponding UserWord for this UserLesson
    lesson_words = myLesson.lesson.words.all()
    existing_userword_word_ids = set(
        UserWord.objects.filter(user_lesson=myLesson).values_list("word_id", flat=True)
    )
    missing_words = [w for w in lesson_words if w.id not in existing_userword_word_ids]
    for word in missing_words:
        UserWord.objects.create(
            user_lesson=myLesson, word=word, current_progress=0, notes=""
        )

    myWords = UserWord.objects.filter(user_lesson=myLesson).order_by(
        Lower("word__prompt")
    )
    my_Words_search_query = request.GET.get("q") or ""

    if my_Words_search_query:
        myWords = myWords.filter(
            Q(word__prompt__icontains=my_Words_search_query)
            | Q(word__translation__icontains=my_Words_search_query)
            | Q(word__usage__icontains=my_Words_search_query)
            | Q(word__hint__icontains=my_Words_search_query)
            | Q(notes__icontains=my_Words_search_query)
        ).order_by(Lower("word__prompt"))

    is_author = myLesson.lesson.author == request.user
    is_private = myLesson.lesson.access_type.name == "private"
    can_edit = (request.user == myLesson.lesson.author or 
                myLesson.lesson.access_type.name in ["write"])

    from ..forms import UserWordForm
    userWordForm = UserWordForm()

    if can_edit and request.method == "POST":
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
            
            # Auto-generate hint if preference is enabled and hint is blank
            if request.user.userprofile.auto_generate_hints and not new_word.hint and new_word.prompt:
                new_word.hint = new_word.prompt[0].upper()
            
            new_word.save()

            # Generate prompt audio
            if new_word.prompt:
                rel_path = generate_audio_file(
                    new_word.prompt,
                    myLesson.lesson.prompt_language,
                    "audio/prompts",
                    f"word_{new_word.id}_prompt.mp3",
                )
                new_word.prompt_audio = rel_path
            # Generate usage audio
            if new_word.usage:
                rel_path = generate_audio_file(
                    new_word.usage,
                    myLesson.lesson.prompt_language,
                    "audio/usages",
                    f"word_{new_word.id}_usage.mp3",
                )
                new_word.usage_audio = rel_path
            new_word.save()

            # Now create the UserWord instance with the new Word
            UserWord.objects.create(
                user_lesson=myLesson,
                word=new_word,
                current_progress=0,
                notes=userWordForm.cleaned_data.get("notes", ""),
            )

            myLesson.lesson.updated = new_word.updated
            myLesson.lesson.changes_log = (
                (myLesson.lesson.changes_log + "\n" if myLesson.lesson.changes_log else "")
                + f"{timezone.now()} Word '{new_word.prompt}' added by {request.user.username}"
            )
            myLesson.lesson.save()
            messages.success(request, "Word created successfully!")
            return redirect("my-lesson-details", my_lesson_id=myLesson.id)

    # Get breadcrumb path from lesson's directory
    current_directory = myLesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
        myLesson.directory = current_directory
        myLesson.save()
    breadcrumb_path = current_directory.get_path()

    context = {
        "my_lesson": myLesson,
        "my_words": myWords,
        "word_form": userWordForm,
        "can_edit": can_edit,
        "is_private": is_private,
        "is_author": is_author,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myLesson,
    }
    return render(request, "base/authenticated/my_lessons/my_lesson_details.html", context)


@login_required(login_url="login")
def deleteMyLesson(request, my_lesson_id):
    """Delete a user's lesson reference or the entire lesson."""
    myLesson = (
        UserLesson.objects.filter(id=my_lesson_id)
        .select_related("lesson", "lesson__author", "lesson__access_type")
        .first()
    )
    if not myLesson:
        return HttpResponse("You do not have this lesson.", status=404)

    user = request.user
    lesson = myLesson.lesson
    is_author = lesson.author == user
    is_private = lesson.access_type.name == "private"

    # Only the owner of the myLesson or superuser can delete
    if user.id != myLesson.user.id and not user.is_superuser:
        return HttpResponse("You are not allowed here!", status=403)

    if request.method == "POST":
        action = request.POST.get("action")
        # Get the directory for redirect before deletion
        redirect_directory = myLesson.directory

        if action == "delete_both":
            # Delete lesson from repository and all related UserLesson
            lesson.delete()
            messages.success(
                request,
                "Lesson and all your references were deleted from the repository.",
            )
            if redirect_directory:
                return redirect("my-lessons-directory", directory_id=redirect_directory.id)
            return redirect("my-lessons")
        elif action == "delete_mylesson":
            myLesson.delete()
            messages.success(
                request,
                "Your lesson reference was deleted. The lesson remains in the repository.",
            )
            if redirect_directory:
                return redirect("my-lessons-directory", directory_id=redirect_directory.id)
            return redirect("my-lessons")

    # Get breadcrumb path from lesson's directory
    current_directory = myLesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "my_lesson": myLesson,
        "is_author": is_author,
        "is_private": is_private,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myLesson,
    }
    return render(request, "base/authenticated/my_lessons/lesson_utils/delete_my_lesson.html", context)


@login_required(login_url="login")
def lessonsRepository(request):
    """Display the public lessons repository."""
    public_lessons = Lesson.objects.filter(
        access_type__name__in=["readonly", "write"]
    ).order_by(Lower("title"))

    lesson_search_query = request.GET.get("q") if request.GET.get("q") != None else ""
    public_lessons = public_lessons.filter(
        Q(title__icontains=lesson_search_query)
        | Q(description__icontains=lesson_search_query)
        | Q(prompt_language__name__icontains=lesson_search_query)
        | Q(translation_language__name__icontains=lesson_search_query)
    ).order_by(Lower("title"))

    context = {
        "public_lessons": public_lessons,
    }
    return render(request, "base/authenticated/lesson_repository/lessons_repository.html", context)


@login_required(login_url="login")
def lessonDetails(request, lesson_id):
    """Display details of a lesson from the repository."""
    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "author", "access_type", "prompt_language", "translation_language"
        ),
        id=lesson_id
    )
    if lesson.access_type.name == "private":
        return HttpResponse("This lesson is not public", status=403)

    user = request.user
    if user.is_authenticated:
        can_import = not UserLesson.objects.filter(user=user, lesson=lesson).exists()
    else:
        can_import = False

    lessonRatings = Rating.objects.filter(lesson=lesson)
    rating_count = lessonRatings.count()
    average_rating = (
        round(lessonRatings.aggregate(Avg("rating"))["rating__avg"], 1)
        if lessonRatings.exists()
        else 0.0
    )

    words = lesson.words.all().order_by(Lower("prompt"))

    context = {
        "lesson": lesson,
        "words": words,
        "can_import": can_import,
        "average_rating": average_rating,
        "rating_count": rating_count,
    }
    return render(request, "base/authenticated/lesson_repository/lesson_details.html", context)


@login_required(login_url="login")
def rateLesson(request, lesson_id):
    """Handle lesson rating."""
    rateLessonForm = RateLessonForm()
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == "POST":
        user = request.user
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
        "lesson": lesson,
    }
    return render(request, "base/authenticated/lesson_repository/rate_lesson.html", context)


@login_required(login_url="login")
def wordDetails(request, lesson_id, prompt):
    """Display word details from the repository."""
    lesson = get_object_or_404(
        Lesson.objects.select_related("access_type"),
        id=lesson_id
    )
    if lesson.access_type.name == "private":
        return HttpResponse("This lesson is not public", status=403)
    word = get_object_or_404(Word, prompt=prompt, lesson=lesson)

    context = {
        "lesson": lesson,
        "word": word,
    }
    return render(request, "base/authenticated/lesson_repository/word_details.html", context)


@login_required(login_url="login")
@transaction.atomic
def importLesson(request, lesson_id):
    """Import a lesson from the repository to user's lessons."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    user = request.user

    if UserLesson.objects.filter(user=user, lesson=lesson).exists():
        return HttpResponse("You have already imported this lesson.", status=400)

    if lesson.access_type.name == "private":
        return HttpResponse("This lesson is private and cannot be imported.", status=403)

    newLesson = UserLesson.objects.create(
        user=user, lesson=lesson, target_progress=user.userprofile.target_progress,
        practice_window=user.userprofile.practice_window,
        allowed_error_margin=user.userprofile.allowed_error_margin,
    )

    words = Word.objects.filter(lesson=lesson)
    UserWord.objects.bulk_create([
        UserWord(user_lesson=newLesson, word=word, current_progress=0, notes="")
        for word in words
    ])
    lesson.changes_log = (
        lesson.changes_log + "\n" if lesson.changes_log else ""
    ) + f"{timezone.now()} Lesson imported by {user.username}"
    lesson.save()

    return redirect("my-lessons")


@login_required(login_url="login")
@transaction.atomic
def createLesson(request):
    """Create a new lesson."""
    # Get current directory from session, or use root directory
    current_directory_id = request.session.get('current_directory_id')
    if current_directory_id:
        current_directory = UserDirectory.objects.filter(
            id=current_directory_id, user=request.user
        ).first()
        if not current_directory:
            current_directory = UserDirectory.get_or_create_root_directory(request.user)
    else:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)

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
            myLesson.directory = current_directory
            myLesson.save()

            messages.success(request, "Lesson created successfully!")
            return redirect("my-lesson-details", my_lesson_id=myLesson.id)
    else:
        user_profile = request.user.userprofile
        user_lesson_form = UserLessonForm(initial={
            'access_type': AccessType.objects.get(name="private"),
            'target_progress': user_profile.target_progress,
            'practice_window': user_profile.practice_window,
            'allowed_error_margin': user_profile.allowed_error_margin,
        })

    # Build breadcrumb for current directory
    breadcrumb_path = current_directory.get_path()

    context = {
        "lesson_form": user_lesson_form,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
    }
    return render(request, "base/authenticated/my_lessons/lesson_utils/create_lesson.html", context)


@login_required(login_url="login")
@transaction.atomic
def copyLesson(request, my_lesson_id):
    """Create a private copy of a lesson."""
    myLesson = UserLesson.objects.select_related(
        "lesson", "lesson__access_type", "lesson__prompt_language", "lesson__translation_language"
    ).filter(id=my_lesson_id).first()
    if not myLesson:
        return HttpResponse("You do not have this lesson.", status=404)

    if request.user.id != myLesson.user.id and not request.user.is_superuser:
        return HttpResponse("You are not allowed here!", status=403)

    # Check if the lesson is private
    if myLesson.lesson.access_type.name == "private":
        return HttpResponse("You cannot copy a private lesson.", status=403)

    # Get or create root directory for the user
    root_directory = UserDirectory.get_or_create_root_directory(request.user)

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
        access_type=AccessType.objects.get(name="private"),
        original_lesson=lesson,
        changes_log=lesson.changes_log,
    )
    new_lesson.save()
    
    # Create a UserLesson for the new lesson
    new_user_lesson = UserLesson.objects.create(
        user=request.user, 
        lesson=new_lesson,
        directory=root_directory
    )

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
            current_progress=0,
            notes="",
        )
    # Remove the original lesson from the UserLesson
    myLesson.delete()

    messages.success(request, "Lesson copied successfully!")
    return redirect("my-lesson-details", my_lesson_id=new_user_lesson.id)


@login_required(login_url="login")
@transaction.atomic
def importAndCopyLesson(request, lesson_id):
    """Import a lesson from repository as a private copy."""
    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "access_type", "prompt_language", "translation_language"
        ),
        id=lesson_id
    )
    user = request.user

    if lesson.access_type.name == "private":
        return HttpResponse("This lesson is private and cannot be imported.", status=403)

    # Get or create root directory for the user
    root_directory = UserDirectory.get_or_create_root_directory(user)

    # Create a new lesson as a copy
    new_lesson = Lesson(
        title=lesson.title,
        description=lesson.description,
        prompt_language=lesson.prompt_language,
        translation_language=lesson.translation_language,
        author=user,
        access_type=AccessType.objects.get(name="private"),
        original_lesson=lesson,
        changes_log="",
    )
    new_lesson.save()

    # Create UserLesson for the new lesson
    new_user_lesson = UserLesson.objects.create(
        user=user, lesson=new_lesson,
        directory=root_directory,
        target_progress=user.userprofile.target_progress,
        practice_window=user.userprofile.practice_window,
        allowed_error_margin=user.userprofile.allowed_error_margin,
    )

    # Copy words to the new lesson using bulk operations
    words = list(lesson.words.all())
    
    # Auto-generate hints for words if preference is enabled
    auto_generate = user.userprofile.auto_generate_hints
    new_words_data = []
    for word in words:
        hint = word.hint
        if auto_generate and not hint and word.prompt:
            hint = word.prompt[0].upper()
        new_words_data.append(Word(
            lesson=new_lesson,
            prompt=word.prompt,
            translation=word.translation,
            usage=word.usage,
            hint=hint,
        ))
    
    new_words = Word.objects.bulk_create(new_words_data)
    UserWord.objects.bulk_create([
        UserWord(
            user_lesson=new_user_lesson,
            word=new_word,
            current_progress=0,
            notes="",
        )
        for new_word in new_words
    ])

    # Update original lesson's changes_log
    lesson.changes_log = (
        lesson.changes_log + "\n" if lesson.changes_log else ""
    ) + f"{timezone.now()} Lesson imported and copied by {user.username}"
    lesson.save()

    messages.success(request, "Lesson imported and copied successfully!")
    return redirect("edit-lesson", my_lesson_id=new_user_lesson.id)


@login_required(login_url="login")
@transaction.atomic
def editLesson(request, my_lesson_id):
    """Edit lesson details."""
    myLesson = UserLesson.objects.select_related(
        "lesson", "lesson__author", "lesson__access_type",
        "lesson__prompt_language", "lesson__translation_language"
    ).filter(id=my_lesson_id).first()

    if not myLesson:
        return HttpResponse("You do not have this lesson.", status=404)

    if request.user.id != myLesson.user.id and not request.user.is_superuser:
        return HttpResponse("You are not allowed here!", status=403)

    if request.user != myLesson.lesson.author:
        return HttpResponse("You do not have rights to edit this lesson!", status=403)

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
        "allowed_error_margin": myLesson.allowed_error_margin,
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

    # Get breadcrumb path from lesson's directory
    current_directory = myLesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "edit_user_lesson_form": edit_user_lesson_form,
        "my_lesson": myLesson,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myLesson,
    }
    return render(request, "base/authenticated/my_lessons/lesson_utils/edit_lesson.html", context)


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def resetProgress(request, my_lesson_id):
    """Reset progress for all words in a lesson."""
    myLesson = get_object_or_404(UserLesson, id=my_lesson_id, user=request.user)

    if request.method == "POST":
        # Reset progress for all UserWords in this UserLesson
        UserWord.objects.filter(user_lesson=myLesson).update(current_progress=0)
        messages.success(
            request, "Progress for all words in this lesson has been reset to 0."
        )
        return redirect("my-lesson-details", my_lesson_id=my_lesson_id)

    # Get breadcrumb path from lesson's directory
    current_directory = myLesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "my_lesson": myLesson,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myLesson,
    }
    return render(request, "base/authenticated/my_lessons/practice/reset_progress.html", context)


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def import_lesson_json(request):
    """Import a lesson from JSON file."""
    if request.method == "POST":
        file = request.FILES.get("json_file")
        if not file:
            messages.error(request, "No file uploaded.")
            return redirect("import-lesson-json")

        # Security: Only allow .json files and limit size (e.g., 1MB)
        if not file.name.endswith(".json") or file.size > 1024 * 1024:
            messages.error(request, "Invalid file type or file too large.")
            return redirect("import-lesson-json")

        try:
            data = json.load(file)
        except Exception as e:
            messages.error(request, f"Invalid JSON: {e}")
            return redirect("import-lesson-json")

        # Validate required fields
        required_fields = ["title", "prompt_language", "translation_language", "words"]
        if not all(field in data for field in required_fields):
            messages.error(request, "Missing required fields in JSON.")
            return redirect("import-lesson-json")

        # Get user profile for auto-generate hints
        user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
        auto_generate = user_profile.auto_generate_hints

        # Get or create languages
        prompt_lang, _ = Language.objects.get_or_create(name=data["prompt_language"])
        translation_lang, _ = Language.objects.get_or_create(
            name=data["translation_language"]
        )

        # AccessType: Only use existing, fallback to 'private'
        access_type_name = data.get("access_type", "private")
        try:
            access_type = AccessType.objects.get(name=access_type_name)
        except AccessType.DoesNotExist:
            access_type = AccessType.objects.get(name="private")

        # Create the lesson
        lesson = Lesson.objects.create(
            title=data["title"],
            description=data.get("description", ""),
            prompt_language=prompt_lang,
            translation_language=translation_lang,
            author=request.user,
            access_type=access_type,
        )

        # Create words
        for word in data.get("words", []):
            # Validate word fields
            if not all(k in word for k in ("prompt", "translation")):
                continue  # skip incomplete word entries
            hint_value = word.get("hint", "")
            if not hint_value and auto_generate and word["prompt"]:
                hint_value = word["prompt"][0].upper()
            Word.objects.create(
                lesson=lesson,
                prompt=word["prompt"],
                translation=word["translation"],
                usage=word.get("usage", ""),
                hint=hint_value,
            )

        # Get or create root directory for the user
        root_directory = UserDirectory.get_or_create_root_directory(request.user)

        # Create UserLesson for the importing user
        user_lesson = UserLesson.objects.create(
            user=request.user, 
            lesson=lesson,
            directory=root_directory
        )

        # Create UserWord for each word
        for word in lesson.words.all():
            UserWord.objects.create(
                user_lesson=user_lesson, word=word, current_progress=0, notes=""
            )

        lesson.changes_log = (
            ((lesson.changes_log + "\n") if lesson.changes_log else "")
            + f"{timezone.now()} Lesson imported by {request.user.username} from file '{file.name}'"
        )
        lesson.save()

        messages.success(request, "Lesson imported successfully!")
        return redirect("my-lesson-details", my_lesson_id=user_lesson.id)

    # Get breadcrumb path for root directory
    root_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = root_directory.get_path()

    context = {
        "breadcrumb_path": breadcrumb_path,
    }   
    
    return render(request, "base/authenticated/my_lessons/lesson_utils/import_lesson_json.html", context)


@login_required(login_url="login")
def export_lesson_json(request, lesson_id):
    """Export a lesson to JSON format."""
    lesson = get_object_or_404(
        Lesson.objects.select_related("author", "prompt_language", "translation_language", "access_type"),
        id=lesson_id
    )

    # Only allow the author or superuser to export
    if request.user != lesson.author and not request.user.is_superuser:
        return HttpResponse("You are not allowed to export this lesson.", status=403)

    words = Word.objects.filter(lesson=lesson)
    data = {
        "title": lesson.title,
        "description": lesson.description,
        "prompt_language": lesson.prompt_language.name,
        "translation_language": lesson.translation_language.name,
        "access_type": lesson.access_type.name,
        "words": [
            {
                "prompt": w.prompt,
                "translation": w.translation,
                "usage": w.usage,
                "hint": w.hint,
            }
            for w in words
        ],
    }

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    filename = f"{lesson.title.replace(' ', '_')}.json"
    response = HttpResponse(json_str, content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url="login")
def generate_lesson_audio_start(request, my_lesson_id):
    """Display confirmation page for audio generation."""
    myLesson = get_object_or_404(UserLesson, id=my_lesson_id, user=request.user)
    
    # Get breadcrumb path from lesson's directory
    current_directory = myLesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "my_lesson": myLesson,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myLesson,
    }
    
    return render(request, "base/authenticated/my_lessons/lesson_utils/generate_lesson_audio.html", context)


@login_required(login_url="login")
@require_POST
def generate_lesson_audio(request, my_lesson_id):
    """Generate audio files for all words in a lesson."""
    myLesson = get_object_or_404(UserLesson, id=my_lesson_id, user=request.user)
    words = myLesson.lesson.words.all()

    for word in words:
        # Generate prompt audio
        if word.prompt:
            if (
                word.prompt_audio
                and word.prompt_audio.path
                and os.path.isfile(word.prompt_audio.path)
            ):
                os.remove(word.prompt_audio.path)
                word.prompt_audio = None
            rel_path = generate_audio_file(
                word.prompt,
                word.lesson.prompt_language,
                "audio/prompts",
                f"word_{word.id}_prompt.mp3",
            )
            word.prompt_audio = rel_path

        # Generate usage audio
        if word.usage:
            if (
                word.usage_audio
                and word.usage_audio.path
                and os.path.isfile(word.usage_audio.path)
            ):
                os.remove(word.usage_audio.path)
                word.usage_audio = None
            rel_path = generate_audio_file(
                word.usage,
                word.lesson.prompt_language,
                "audio/usages",
                f"word_{word.id}_usage.mp3",
            )
            word.usage_audio = rel_path

        word.save()

    myLesson.lesson.updated = timezone.now()
    myLesson.lesson.changes_log = (
        (myLesson.lesson.changes_log + "\n" if myLesson.lesson.changes_log else "")
        + f"{timezone.now()} Audio files generated for lesson by {request.user.username}"
    )
    myLesson.lesson.save()
    messages.success(request, "Audio files generated successfully!")
    return redirect("my-lesson-details", my_lesson_id=myLesson.id)


@login_required(login_url="login")
def moveLesson(request, my_lesson_id):
    """Move a lesson to a different directory."""
    user_lesson = get_object_or_404(UserLesson, id=my_lesson_id, user=request.user)
    
    current_directory_id = user_lesson.directory.id if user_lesson.directory else None
    
    if request.method == "POST":
        form = MoveLessonForm(request.POST, user=request.user)
        if form.is_valid():
            new_directory = form.cleaned_data["directory"]
            user_lesson.directory = new_directory
            user_lesson.save()
            messages.success(request, f"Lesson '{user_lesson.lesson.title}' moved successfully!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect("my-lessons-directory", directory_id=new_directory.id)
    else:
        form = MoveLessonForm(user=request.user)
        if user_lesson.directory:
            form.fields["directory"].initial = user_lesson.directory
    
    cancel_url = request.GET.get('next') or (reverse('my-lessons-directory', kwargs={'directory_id': current_directory_id}) if current_directory_id else reverse('my-lessons'))
    
    # Build breadcrumb path
    breadcrumb_path = user_lesson.directory.get_path() if user_lesson.directory else []

    context = {
        "form": form,
        "user_lesson": user_lesson,
        "cancel_url": cancel_url,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": user_lesson,
    }
    return render(request, "base/authenticated/my_lessons/fs_utils/move_lesson.html", context)
