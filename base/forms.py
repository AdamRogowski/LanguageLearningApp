from django.forms import ModelForm
from .models import Room, Lesson, Word
from django import forms


class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = "__all__"
        exclude = ["host", "participants"]


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


class WordForm(ModelForm):
    class Meta:
        model = Word
        fields = "__all__"
        exclude = ["lesson", "created", "updated"]
        widgets = {
            "prompt": forms.TextInput(attrs={"autofocus": "autofocus"}),
        }
