from django.db import models
from django.contrib.auth.models import User

# Language learning app models


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
    description = models.TextField()
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


class Word(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="words")
    prompt = models.CharField(max_length=255)
    translation = models.CharField(max_length=255)
    usage = models.TextField(blank=True)
    hint = models.CharField(max_length=255, blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.prompt} -> {self.translation}"


class UserLesson(models.Model):
    """
    Mapping of user-specific progress with a lesson.
    Represents the act of importing a lesson for individual study.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    target_progress = models.IntegerField(default=3)
    lesson_directory = models.CharField(
        max_length=255, blank=True, help_text="Directory where the lesson is stored."
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
