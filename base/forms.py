from django.forms import ModelForm
from .models import Room, Topic, Message


class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = "__all__"
        exclude = ["host", "participants"]


# class UserWordForm(ModelForm):
#    class Meta:
#        model = Topic
#        fields = "__all__"
#        exclude = []
