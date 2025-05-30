from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import os
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

# Language learning app models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Example preferences:
    display_name = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(max_length=50, blank=True)
    receive_notifications = models.BooleanField(default=True)
    # Add more fields as needed

    def __str__(self):
        return f"Profile of {self.user.username}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.userprofile.save()


class AccessType(models.Model):
    """
    Controls access and editing rights for a lesson.
    Examples: Private, Read-only (Public but uneditable), Write (Public and editable).
    """

    ACCESS_CHOICES = [
        ("private", "Private"),
        ("readonly", "Read-Only"),
        ("write", "Writable"),
    ]

    name = models.CharField(max_length=20, choices=ACCESS_CHOICES, unique=True)

    def __str__(self):
        return self.get_name_display()


class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    """
    Represents a language lesson, potentially public and reused by multiple users.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(
        blank=True, help_text="Brief description of the lesson."
    )
    prompt_language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name="prompt_lessons"
    )
    translation_language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name="translation_lessons"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="authored_lessons",
    )

    # TODO: Uncomment if contributors are needed
    # To track contributors to the lesson; can be useful for collaborative lessons or community contributions.
    # contributors = models.ManyToManyField(
    #    User,
    #    related_name="contributed_lessons",
    #    blank=True,
    # )

    changes_log = models.TextField(
        blank=True, help_text="Log of changes made to this lesson."
    )

    access_type = models.ForeignKey(AccessType, on_delete=models.PROTECT, default=1)

    original_lesson = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.author.username}"


@receiver(pre_delete, sender=Lesson)
def delete_lesson_audio_files(sender, instance, **kwargs):
    for word in instance.words.all():
        if (
            word.prompt_audio
            and word.prompt_audio.path
            and os.path.isfile(word.prompt_audio.path)
        ):
            os.remove(word.prompt_audio.path)
        if (
            word.usage_audio
            and word.usage_audio.path
            and os.path.isfile(word.usage_audio.path)
        ):
            os.remove(word.usage_audio.path)


class Word(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="words")
    prompt = models.CharField(max_length=255)
    translation = models.CharField(max_length=255)
    usage = models.TextField(blank=True)
    prompt_audio = models.FileField(upload_to="audio/prompts/", blank=True, null=True)
    usage_audio = models.FileField(upload_to="audio/usages/", blank=True, null=True)
    hint = models.CharField(max_length=255, blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        # Delete prompt audio file if it exists
        if (
            self.prompt_audio
            and self.prompt_audio.path
            and os.path.isfile(self.prompt_audio.path)
        ):
            os.remove(self.prompt_audio.path)
        # Delete usage audio file if it exists
        if (
            self.usage_audio
            and self.usage_audio.path
            and os.path.isfile(self.usage_audio.path)
        ):
            os.remove(self.usage_audio.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.prompt} -> {self.translation}"


@receiver(pre_delete, sender=Word)
def delete_word_audio_files(sender, instance, **kwargs):
    if (
        instance.prompt_audio
        and instance.prompt_audio.path
        and os.path.isfile(instance.prompt_audio.path)
    ):
        os.remove(instance.prompt_audio.path)
    if (
        instance.usage_audio
        and instance.usage_audio.path
        and os.path.isfile(instance.usage_audio.path)
    ):
        os.remove(instance.usage_audio.path)


class UserLesson(models.Model):
    """
    Mapping of user-specific progress with a lesson.
    Represents the act of importing a lesson for individual study.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    target_progress = models.PositiveIntegerField(
        default=3, validators=[MinValueValidator(1)]
    )
    practice_window = models.PositiveIntegerField(
        default=10, validators=[MinValueValidator(1)]
    )
    allowed_error_margin = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0)]
    )

    class Meta:
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"


class UserWord(models.Model):
    user_lesson = models.ForeignKey(
        UserLesson,
        on_delete=models.CASCADE,
        related_name="user_words",
    )
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    current_progress = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("user_lesson", "word")

    def __str__(self):
        return f"{self.word.prompt} ({self.user_lesson.user.username})"


class Rating(models.Model):
    """
    Represents a rating given by a user to a lesson.
    Rating must be an integer from 1 to 5.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        default=1,
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Rating must be an integer from 1 to 5.",
    )

    class Meta:
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user.username} rated {self.lesson.title} with {self.rating}"


"""

class UserDirectory(models.Model):

    name = models.CharField(max_length=255)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )  # Redundant field to link to User to help with queries
    userLesson = models.ForeignKey(UserLesson, on_delete=models.CASCADE)
    parent_directory = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subdirectories",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.userLesson.user.username})"
"""
