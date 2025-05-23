from django.contrib import admin

# Register your models here.

from .models import Room, Topic, Message

admin.site.register(Topic)
admin.site.register(Room)
admin.site.register(Message)
admin.site.site_header = "Language Learning App Admin"
admin.site.site_title = "Language Learning App Admin Portal"
admin.site.index_title = "Welcome to the Language Learning App Admin Portal"
from .models import Language, Lesson, Word, UserLesson, UserWord

admin.site.register(Language)
admin.site.register(Lesson)
admin.site.register(Word)
admin.site.register(UserLesson)
admin.site.register(UserWord)
