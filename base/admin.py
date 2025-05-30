from django.contrib import admin

# Register your models here.


admin.site.site_header = "Language Learning App Admin"
admin.site.site_title = "Language Learning App Admin Portal"
admin.site.index_title = "Welcome to the Language Learning App Admin Portal"
from .models import (
    Language,
    Lesson,
    Word,
    UserLesson,
    UserWord,
    AccessType,
    Rating,
    UserProfile,
)

admin.site.register(Language)
admin.site.register(Lesson)
admin.site.register(Word)
admin.site.register(UserLesson)
admin.site.register(UserWord)
admin.site.register(AccessType)
admin.site.register(Rating)
admin.site.register(UserProfile)
