from django.forms import ModelForm
from .models import Word, UserLesson, Language, AccessType, UserWord, UserProfile, UserDirectory
from django import forms
from django.contrib.auth.models import User


class UserLessonForm(forms.ModelForm):
    class Meta:
        model = UserLesson
        fields = [
            "title",
            "description",
            "prompt_language",
            "translation_language",
            "access_type",
            "target_progress",
            "practice_window",
            "allowed_error_margin",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": "autofocus"}),
            "target_progress": forms.NumberInput(attrs={"min": 1}),
            "practice_window": forms.NumberInput(attrs={"min": 1}),
        }

    # Override fields from Lesson as unbound fields
    title = forms.CharField(
        widget=forms.TextInput(attrs={"autofocus": "autofocus"}), required=True
    )
    description = forms.CharField(widget=forms.Textarea, required=False)
    prompt_language = forms.ModelChoiceField(
        queryset=Language.objects.all(), required=True
    )
    translation_language = forms.ModelChoiceField(
        queryset=Language.objects.all(), required=True
    )
    access_type = forms.ModelChoiceField(
        queryset=AccessType.objects.all(), required=True
    )
    target_progress = forms.IntegerField(min_value=1, required=True)
    practice_window = forms.IntegerField(min_value=1, required=True)
    allowed_error_margin = forms.IntegerField(min_value=0, required=True)

    def __init__(self, *args, lesson_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        if lesson_instance:
            self.fields["title"].initial = lesson_instance.title
            self.fields["description"].initial = lesson_instance.description
            self.fields["prompt_language"].initial = lesson_instance.prompt_language
            self.fields["translation_language"].initial = (
                lesson_instance.translation_language
            )
            self.fields["access_type"].initial = lesson_instance.access_type


class UserWordForm(forms.ModelForm):
    class Meta:
        model = UserWord
        fields = ["prompt", "translation", "usage", "hint", "notes"]
        widgets = {
            "translation": forms.TextInput(),
            "usage": forms.Textarea(attrs={"rows": 3}),
            "hint": forms.TextInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    # Only prompt and translation are required
    prompt = forms.CharField(
        label="Prompt",
        widget=forms.TextInput(attrs={"autofocus": "autofocus"}),
        required=True,
    )
    translation = forms.CharField(label="Translation", required=True)
    usage = forms.CharField(
        label="Usage", widget=forms.Textarea(attrs={"rows": 3}), required=False
    )
    hint = forms.CharField(label="Hint", required=False)
    notes = forms.CharField(
        label="Notes", widget=forms.Textarea(attrs={"rows": 3}), required=False
    )

    def __init__(self, *args, word_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        if word_instance:
            self.fields["prompt"].initial = word_instance.prompt
            self.fields["translation"].initial = word_instance.translation
            self.fields["usage"].initial = word_instance.usage
            self.fields["hint"].initial = word_instance.hint


class WordForm(ModelForm):
    class Meta:
        model = Word
        fields = "__all__"
        exclude = ["lesson", "created", "updated"]
        widgets = {
            "prompt": forms.TextInput(attrs={"autofocus": "autofocus"}),
        }


class RateLessonForm(forms.Form):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={"class": "form-control", "autofocus": "autofocus"}),
        label="Rate this lesson (1-5)",
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["display_name", "preferred_language", "receive_notifications", "target_progress", "practice_window", "allowed_error_margin"]


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class UserDirectoryForm(forms.ModelForm):
    class Meta:
        model = UserDirectory
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"autofocus": "autofocus", "placeholder": "Folder name"}),
        }

    def __init__(self, *args, user=None, parent_directory=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.parent_directory = parent_directory

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            if not name:
                raise forms.ValidationError("Folder name cannot be empty.")
            # Check for duplicate names in the same parent directory
            existing = UserDirectory.objects.filter(
                user=self.user,
                parent_directory=self.parent_directory,
                name__iexact=name
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("A folder with this name already exists in this location.")
        return name


class MoveLessonForm(forms.Form):
    """Form for moving a lesson to a different directory."""
    directory = forms.ModelChoiceField(
        queryset=UserDirectory.objects.none(),
        label="Move to folder",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["directory"].queryset = UserDirectory.objects.filter(user=user).order_by("name")


class MoveDirectoryForm(forms.Form):
    """Form for moving a directory to a different parent directory."""
    parent_directory = forms.ModelChoiceField(
        queryset=UserDirectory.objects.none(),
        label="Move to folder",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, user=None, current_directory=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Exclude the current directory and its subdirectories to prevent circular references
            excluded_ids = [current_directory.id] if current_directory else []
            if current_directory:
                # Get all descendant directory IDs
                def get_descendant_ids(directory):
                    ids = []
                    for subdir in directory.subdirectories.all():
                        ids.append(subdir.id)
                        ids.extend(get_descendant_ids(subdir))
                    return ids
                excluded_ids.extend(get_descendant_ids(current_directory))
            
            self.fields["parent_directory"].queryset = UserDirectory.objects.filter(
                user=user
            ).exclude(id__in=excluded_ids).order_by("name")
