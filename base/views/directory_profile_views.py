"""Directory and profile views: user settings and filesystem operations."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
import os

from ..models import UserDirectory, UserLesson, UserProfile
from ..forms import UserDirectoryForm, MoveLessonForm, MoveDirectoryForm
from ..forms import UserProfileForm, UserForm
from ..models import Lesson, Word


@login_required(login_url="login")
def profile_view(request):
    """Display user profile information."""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    user = request.user
    memory_bytes = get_user_memory_usage(user)
    memory_mb = round(memory_bytes / (1024 * 1024), 2)

    context = {
        "user_profile": user_profile,
        "memory_usage_mb": memory_mb,
    }

    return render(request, "base/authenticated/user_profile/profile.html", context)


@login_required(login_url="login")
def settings_view(request):
    """Handle user settings updates."""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=user_profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your settings have been updated.")
            return redirect("profile")
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)
    return render(
        request,
        "base/authenticated/user_profile/settings.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


def get_user_memory_usage(user):
    """Calculate total memory usage for a user's lessons and audio."""
    total_chars = 0
    total_audio_bytes = 0

    # Get all lessons authored by the user
    lessons = Lesson.objects.filter(author=user)

    for lesson in lessons:
        # Sum metadata fields for the lesson
        total_chars += len(lesson.title or "")
        total_chars += len(lesson.description or "")
        total_chars += len(
            lesson.prompt_language.name if lesson.prompt_language else ""
        )
        total_chars += len(
            lesson.translation_language.name if lesson.translation_language else ""
        )
        total_chars += len(lesson.access_type.name if lesson.access_type else "")

        # For each word in the lesson
        for word in lesson.words.all():
            total_chars += len(word.prompt or "")
            total_chars += len(word.translation or "")
            total_chars += len(word.usage or "")
            total_chars += len(word.hint or "")

            # Add audio file sizes if they exist
            if (
                word.prompt_audio
                and word.prompt_audio.path
                and os.path.isfile(word.prompt_audio.path)
            ):
                total_audio_bytes += os.path.getsize(word.prompt_audio.path)
            if (
                word.usage_audio
                and word.usage_audio.path
                and os.path.isfile(word.usage_audio.path)
            ):
                total_audio_bytes += os.path.getsize(word.usage_audio.path)

    # Each character is 1 byte in UTF-8 for plain ASCII, but could be more for Unicode.
    # For a rough estimate, assume 1 char = 1 byte.
    total_bytes = total_chars + total_audio_bytes
    return total_bytes


@login_required(login_url="login")
def createDirectory(request, directory_id):
    """Create a new directory within the specified parent directory."""
    parent_directory = get_object_or_404(UserDirectory, id=directory_id, user=request.user)
    
    if request.method == "POST":
        form = UserDirectoryForm(request.POST, user=request.user, parent_directory=parent_directory)
        if form.is_valid():
            directory = form.save(commit=False)
            directory.user = request.user
            directory.parent_directory = parent_directory
            directory.save()
            messages.success(request, f"Folder '{directory.name}' created successfully!")
            return redirect("my-lessons-directory", directory_id=parent_directory.id)
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    else:
        form = UserDirectoryForm(user=request.user, parent_directory=parent_directory)
    
    # Build breadcrumb for parent directory
    breadcrumb_path = parent_directory.get_path()
    
    context = {
        "form": form,
        "parent_directory": parent_directory,
        "breadcrumb_path": breadcrumb_path,
    }
    return render(request, "base/authenticated/my_lessons/fs_utils/create_directory.html", context)


@login_required(login_url="login")
def renameDirectory(request, directory_id):
    """Rename an existing directory."""
    directory = get_object_or_404(UserDirectory, id=directory_id, user=request.user)
    
    if directory.is_root:
        messages.error(request, "Cannot rename the Home folder.")
        return redirect("my-lessons")
    
    parent_id = directory.parent_directory.id if directory.parent_directory else None
    
    if request.method == "POST":
        form = UserDirectoryForm(
            request.POST, 
            instance=directory, 
            user=request.user, 
            parent_directory=directory.parent_directory
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"Folder renamed to '{directory.name}' successfully!")
            if parent_id:
                return redirect("my-lessons-directory", directory_id=parent_id)
            return redirect("my-lessons")
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    else:
        form = UserDirectoryForm(instance=directory, user=request.user, parent_directory=directory.parent_directory)
    
    # Build breadcrumb path
    breadcrumb_path = directory.parent_directory.get_path()
    
    context = {
        "form": form,
        "directory": directory,
        "breadcrumb_path": breadcrumb_path,
    }
    return render(request, "base/authenticated/my_lessons/fs_utils/rename_directory.html", context)


@login_required(login_url="login")
def moveDirectory(request, directory_id):
    """Move a directory to a different parent directory."""
    directory = get_object_or_404(UserDirectory, id=directory_id, user=request.user)
    
    if directory.is_root:
        messages.error(request, "Cannot move the Home folder.")
        return redirect("my-lessons")
    
    original_parent_id = directory.parent_directory.id if directory.parent_directory else None
    
    if request.method == "POST":
        form = MoveDirectoryForm(request.POST, user=request.user, current_directory=directory)
        if form.is_valid():
            new_parent = form.cleaned_data["parent_directory"]
            # Check that we're not moving to the same location
            if new_parent.id == original_parent_id:
                messages.info(request, "Folder is already in this location.")
            else:
                directory.parent_directory = new_parent
                directory.save()
                messages.success(request, f"Folder '{directory.name}' moved successfully!")
            return redirect("my-lessons-directory", directory_id=new_parent.id)
    else:
        form = MoveDirectoryForm(user=request.user, current_directory=directory)
    
    # Build breadcrumb path
    breadcrumb_path = directory.parent_directory.get_path()
    
    context = {
        "form": form,
        "directory": directory,
        "breadcrumb_path": breadcrumb_path,
    }
    return render(request, "base/authenticated/my_lessons/fs_utils/move_directory.html", context)


@login_required(login_url="login")
def deleteDirectory(request, directory_id):
    """Delete a directory and optionally its contents."""
    directory = get_object_or_404(UserDirectory, id=directory_id, user=request.user)
    
    if directory.is_root:
        messages.error(request, "Cannot delete the Home folder.")
        return redirect("my-lessons")
    
    parent_id = directory.parent_directory.id if directory.parent_directory else None
    
    # Count contents for warning
    subdirectory_count = directory.subdirectories.count()
    lesson_count = directory.lessons.count()
    
    if request.method == "POST":
        action = request.POST.get("action", "cancel")
        
        if action == "delete_all":
            # Delete directory and all contents (cascade will handle it)
            directory_name = directory.name
            directory.delete()
            messages.success(request, f"Folder '{directory_name}' and all its contents deleted successfully!")
        elif action == "move_contents":
            # Move all contents to parent directory, then delete the empty directory
            parent = directory.parent_directory
            
            # Move subdirectories
            for subdir in directory.subdirectories.all():
                subdir.parent_directory = parent
                subdir.save()
            
            # Move lessons
            for lesson in directory.lessons.all():
                lesson.directory = parent
                lesson.save()
            
            directory_name = directory.name
            directory.delete()
            messages.success(request, f"Contents moved and folder '{directory_name}' deleted successfully!")
        else:
            # Cancel
            messages.info(request, "Deletion cancelled.")
        
        if parent_id:
            return redirect("my-lessons-directory", directory_id=parent_id)
        return redirect("my-lessons")
    
    # Build breadcrumb path
    breadcrumb_path = directory.parent_directory.get_path()
    
    context = {
        "directory": directory,
        "subdirectory_count": subdirectory_count,
        "lesson_count": lesson_count,
        "has_contents": subdirectory_count > 0 or lesson_count > 0,
        "breadcrumb_path": breadcrumb_path,
    }
    return render(request, "base/authenticated/my_lessons/fs_utils/delete_directory.html", context)


@login_required(login_url="login")
@require_POST
def dragDropMove(request):
    """Handle drag-and-drop move operations for lessons and directories."""
    item_type = request.POST.get("item_type")
    item_id = request.POST.get("item_id")
    target_directory_id = request.POST.get("target_directory_id")
    # Get the directory where the move was initiated (source directory)
    source_directory_id = request.POST.get("source_directory_id")
    
    if not all([item_type, item_id, target_directory_id]):
        messages.error(request, "Invalid move operation.")
        return redirect("my-lessons")
    
    try:
        item_id = int(item_id)
        target_directory_id = int(target_directory_id)
    except ValueError:
        messages.error(request, "Invalid move operation.")
        return redirect("my-lessons")
    
    # Get target directory
    target_directory = get_object_or_404(UserDirectory, id=target_directory_id, user=request.user)
    
    if item_type == "lesson":
        user_lesson = get_object_or_404(UserLesson, id=item_id, user=request.user)
        source_directory = user_lesson.directory
        
        if source_directory and source_directory.id == target_directory_id:
            messages.info(request, "Lesson is already in this folder.")
        else:
            user_lesson.directory = target_directory
            user_lesson.save()
            messages.success(request, f"Lesson '{user_lesson.lesson.title}' moved to '{target_directory.name}'!")
        
    elif item_type == "directory":
        directory = get_object_or_404(UserDirectory, id=item_id, user=request.user)
        
        if directory.is_root:
            messages.error(request, "Cannot move the Home folder.")
        elif directory.id == target_directory_id:
            messages.info(request, "Cannot move folder into itself.")
        else:
            # Check for circular reference (target is a descendant of source)
            def is_descendant(potential_ancestor, potential_descendant):
                current = potential_descendant
                while current is not None:
                    if current.id == potential_ancestor.id:
                        return True
                    current = current.parent_directory
                return False
            
            if is_descendant(directory, target_directory):
                messages.error(request, "Cannot move a folder into one of its subfolders.")
            elif directory.parent_directory and directory.parent_directory.id == target_directory_id:
                messages.info(request, "Folder is already in this location.")
            else:
                directory.parent_directory = target_directory
                directory.save()
                messages.success(request, f"Folder '{directory.name}' moved to '{target_directory.name}'!")
    else:
        messages.error(request, "Invalid item type.")
    
    # Redirect to the directory where the move was initiated, or to 'my-lessons' if unknown
    if source_directory_id:
        try:
            source_directory_id = int(source_directory_id)
            return redirect("my-lessons-directory", directory_id=source_directory_id)
        except Exception:
            pass
    return redirect("my-lessons")
