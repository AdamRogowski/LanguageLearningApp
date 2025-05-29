from django.forms import ModelForm
from .models import Lesson, Word, UserLesson, Language, AccessType, UserWord
from django import forms


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
