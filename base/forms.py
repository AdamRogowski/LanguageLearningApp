from django.forms import ModelForm
from .models import Lesson, Word, UserLesson, Language, AccessType
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
    title = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)
    prompt_language = forms.ModelChoiceField(queryset=Language.objects.all())
    translation_language = forms.ModelChoiceField(queryset=Language.objects.all())
    access_type = forms.ModelChoiceField(queryset=AccessType.objects.all())
    target_progress = forms.IntegerField(min_value=1)
    practice_window = forms.IntegerField(min_value=1)

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
