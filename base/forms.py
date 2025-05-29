from django.forms import ModelForm
from .models import Lesson, Word, UserLesson
from django import forms


class LessonForm(ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title",
            "description",
            "prompt_language",
            "translation_language",
            "access_type",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": "autofocus"}),
        }


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
        }

    # Override fields from Lesson as unbound fields
    title = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)
    prompt_language = forms.CharField()
    translation_language = forms.CharField()
    access_type = forms.ChoiceField(
        choices=Lesson._meta.get_field("access_type").choices
    )

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
