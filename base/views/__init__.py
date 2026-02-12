"""
Views package for the language learning application.

This package organizes views into logical modules:
- auth_views: User authentication (login, logout, register)
- lesson_views: Lesson CRUD, import/export, repository
- word_views: Word CRUD operations
- practice_views: Practice session management
- directory_profile_views: User directories and profile settings
"""

# Authentication views
from .auth_views import (
    loginPage,
    logoutUser,
    registerPage,
)

# Lesson views
from .lesson_views import (
    home,
    myLessons,
    myLessonDetails,
    deleteMyLesson,
    lessonsRepository,
    lessonDetails,
    rateLesson,
    wordDetails,
    importLesson,
    createLesson,
    copyLesson,
    importAndCopyLesson,
    editLesson,
    resetProgress,
    import_lesson_json,
    export_lesson_json,
    generate_lesson_audio_start,
    generate_lesson_audio,
    moveLesson,
)

# Word views
from .word_views import (
    myWordDetails,
    createWord,
    editWord,
    updateNotes,
    deleteWord,
)

# Practice views
from .practice_views import (
    start_practice,
    practice,
    practice_feedback,
    cancel_practice,
)

# Directory and profile views
from .directory_profile_views import (
    profile_view,
    settings_view,
    createDirectory,
    renameDirectory,
    moveDirectory,
    deleteDirectory,
    dragDropMove,
)

__all__ = [
    # Authentication
    'loginPage',
    'logoutUser',
    'registerPage',
    # Lessons
    'home',
    'myLessons',
    'myLessonDetails',
    'deleteMyLesson',
    'lessonsRepository',
    'lessonDetails',
    'rateLesson',
    'wordDetails',
    'importLesson',
    'createLesson',
    'copyLesson',
    'importAndCopyLesson',
    'editLesson',
    'resetProgress',
    'import_lesson_json',
    'export_lesson_json',
    'generate_lesson_audio_start',
    'generate_lesson_audio',
    'moveLesson',
    # Words
    'myWordDetails',
    'createWord',
    'editWord',
    'updateNotes',
    'deleteWord',
    # Practice
    'start_practice',
    'practice',
    'practice_feedback',
    'cancel_practice',
    # Directory & Profile
    'profile_view',
    'settings_view',
    'createDirectory',
    'renameDirectory',
    'moveDirectory',
    'deleteDirectory',
    'dragDropMove',
]
