"""Word management views: CRUD operations for words."""
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models.functions import Lower
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
import os

from ..models import Word, UserWord, UserLesson, UserDirectory
from ..forms import UserWordForm
from ..utils_tts import generate_audio_file


@login_required(login_url="login")
def myWordDetails(request, my_word_id):
    """Display details of a specific user word."""
    myWord = UserWord.objects.select_related(
        "user_lesson", "user_lesson__user", "user_lesson__directory", "word"
    ).filter(id=my_word_id).first()
    if not myWord:
        return HttpResponse("You do not have this word in your lesson.", status=404)

    if (
        request.user.id != myWord.user_lesson.user.id
        and not request.user.is_superuser
    ):
        return HttpResponse("You are not allowed here!", status=403)

    # Get breadcrumb path from lesson's directory
    current_directory = myWord.user_lesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "my_word": myWord,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myWord.user_lesson,
    }
    return render(request, "base/authenticated/my_lessons/my_word_details.html", context)


@login_required(login_url="login")
@transaction.atomic
def createWord(request, my_lesson_id):
    """Create a new word in a lesson."""
    myLesson = UserLesson.objects.select_related(
        "lesson", "lesson__author", "lesson__access_type", 
        "lesson__prompt_language", "lesson__translation_language"
    ).filter(id=my_lesson_id).first()

    if not myLesson:
        return HttpResponse("You do not have this lesson.", status=404)

    if request.user.id != myLesson.user.id and not request.user.is_superuser:
        return HttpResponse("You are not allowed here!", status=403)

    if not (
        request.user == myLesson.lesson.author
        or myLesson.lesson.access_type.name in ["write"]
    ):
        return HttpResponse("You do not have rights to edit this lesson!", status=403)

    # Detect if coming from practice session
    next_url = request.GET.get("next")
    
    if request.method == "POST":
        create_word_form = UserWordForm(request.POST)
        
        if create_word_form.is_valid():
            prompt = create_word_form.cleaned_data["prompt"]
            translation = create_word_form.cleaned_data["translation"]
            usage = create_word_form.cleaned_data["usage"]
            hint = create_word_form.cleaned_data["hint"]
            notes = create_word_form.cleaned_data["notes"]

            # Check if the word already exists in the lesson
            if Word.objects.filter(prompt=prompt, lesson=myLesson.lesson).exists():
                messages.error(request, "This word already exists in the lesson.")
                return redirect("create-word", my_lesson_id=myLesson.id)

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
                notes=notes,
            )

            myLesson.lesson.updated = new_word.updated
            myLesson.lesson.changes_log = (
                (myLesson.lesson.changes_log + "\n" if myLesson.lesson.changes_log else "")
                + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Added word: {new_word.prompt}"
            )
            myLesson.lesson.save()

            messages.success(request, f"Word '{new_word.prompt}' added successfully.")

            # Determine where to redirect
            if next_url:
                return redirect(next_url)
            elif "save_and_close" in request.POST:
                # Only go back to lesson details when explicitly clicking "Save and close"
                return redirect("my-lesson-details", my_lesson_id=myLesson.id)
            else:
                # Default behavior: create another word (when pressing Enter or clicking "Create another")
                return redirect("create-word", my_lesson_id=myLesson.id)
    else:
        create_word_form = UserWordForm()

    # Get breadcrumb path from lesson's directory
    current_directory = myLesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "create_word_form": create_word_form,
        "my_lesson": myLesson,
        "next_url": next_url,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myLesson,
    }
    return render(request, "base/authenticated/my_lessons/word_utils/create_word.html", context)


@login_required(login_url="login")
@transaction.atomic
def editWord(request, my_word_id):
    """Edit an existing word."""
    myWord = UserWord.objects.select_related(
        "user_lesson", "user_lesson__user", "user_lesson__lesson",
        "user_lesson__lesson__author", "user_lesson__lesson__access_type",
        "user_lesson__lesson__prompt_language", "word"
    ).filter(id=my_word_id).first()

    if not myWord:
        return HttpResponse("You do not have this word in your lesson.", status=404)

    if (
        request.user.id != myWord.user_lesson.user.id
        and not request.user.is_superuser
    ):
        return HttpResponse("You are not allowed here!", status=403)

    if not (
        request.user == myWord.user_lesson.lesson.author
        or myWord.user_lesson.lesson.access_type.name in ["write"]
    ):
        return HttpResponse("You do not have rights to edit this lesson!", status=403)

    # Detect if coming from practice session
    next_url = request.GET.get("next")
    
    if request.method == "POST":
        edit_word_form = UserWordForm(
            request.POST, instance=myWord, word_instance=myWord.word
        )
        if edit_word_form.is_valid():
            old_prompt = myWord.word.prompt
            old_usage = myWord.word.usage

            # Update Word fields
            myWord.word.prompt = edit_word_form.cleaned_data["prompt"]
            myWord.word.translation = edit_word_form.cleaned_data["translation"]
            myWord.word.usage = edit_word_form.cleaned_data["usage"]
            myWord.word.hint = edit_word_form.cleaned_data["hint"]
            myWord.word.save()

            # Check if prompt changed
            if myWord.word.prompt and myWord.word.prompt != old_prompt:
                # Remove old prompt audio file if it exists
                if (
                    myWord.word.prompt_audio
                    and myWord.word.prompt_audio.path
                    and os.path.isfile(myWord.word.prompt_audio.path)
                ):
                    os.remove(myWord.word.prompt_audio.path)
                    myWord.word.prompt_audio = None
                rel_path = generate_audio_file(
                    myWord.word.prompt,
                    myWord.word.lesson.prompt_language,
                    "audio/prompts",
                    f"word_{myWord.word.id}_prompt.mp3",
                )
                myWord.word.prompt_audio = rel_path

            # Check if usage changed
            if myWord.word.usage and myWord.word.usage != old_usage:
                # Remove old usage audio file if it exists
                if (
                    myWord.word.usage_audio
                    and myWord.word.usage_audio.path
                    and os.path.isfile(myWord.word.usage_audio.path)
                ):
                    os.remove(myWord.word.usage_audio.path)
                    myWord.word.usage_audio = None
                rel_path = generate_audio_file(
                    myWord.word.usage,
                    myWord.word.lesson.prompt_language,
                    "audio/usages",
                    f"word_{myWord.word.id}_usage.mp3",
                )
                myWord.word.usage_audio = rel_path

            myWord.word.save()
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

            messages.success(request, "Word updated successfully!")
            # Redirect back to practice if 'next' is set, else to lesson details
            if next_url:
                return redirect(next_url)
            return redirect("my-lesson-details", my_lesson_id=myWord.user_lesson.id)
    else:
        edit_word_form = UserWordForm(instance=myWord, word_instance=myWord.word)

    # Get breadcrumb path from lesson's directory
    current_directory = myWord.user_lesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "edit_word_form": edit_word_form,
        "my_word": myWord,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myWord.user_lesson,
    }
    return render(request, "base/authenticated/my_lessons/word_utils/edit_word.html", context)


@login_required(login_url="login")
def updateNotes(request, my_word_id):
    """Update notes for a word via AJAX."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        myWord = UserWord.objects.select_related(
            "user_lesson", "user_lesson__user", "user_lesson__lesson",
            "user_lesson__lesson__author", "user_lesson__lesson__access_type", "word"
        ).filter(id=my_word_id).first()

        if not myWord:
            return JsonResponse({"error": "Word not found"}, status=404)

        if request.user.id != myWord.user_lesson.user.id and not request.user.is_superuser:
            return JsonResponse({"error": "Permission denied"}, status=403)

        notes = request.POST.get("notes", "")
        myWord.notes = notes
        myWord.save()

        return JsonResponse({"success": True, "notes": notes})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required(login_url="login")
@transaction.atomic
def deleteWord(request, my_word_id):
    """Delete a word from a lesson."""
    myWord = UserWord.objects.select_related(
        "user_lesson", "user_lesson__user", "user_lesson__lesson",
        "user_lesson__lesson__author", "user_lesson__lesson__access_type", "word"
    ).filter(id=my_word_id).first()
    user = request.user

    if not myWord:
        return HttpResponse("You do not have this word in your lesson.", status=404)

    myLesson = myWord.user_lesson
    wordNameToDelete = myWord.word.prompt

    if user.id != myWord.user_lesson.user.id and not user.is_superuser:
        return HttpResponse("You are not allowed here!", status=403)

    if not (
        user == myWord.user_lesson.lesson.author
        or myWord.user_lesson.lesson.access_type.name in ["write"]
    ):
        return HttpResponse("You do not have rights to edit this lesson!", status=403)

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

    # Get breadcrumb path from lesson's directory
    current_directory = myWord.user_lesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    context = {
        "my_word": myWord,
        "current_directory": current_directory,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": myWord.user_lesson,
    }

    return render(request, "base/authenticated/my_lessons/word_utils/delete_word.html", context)
