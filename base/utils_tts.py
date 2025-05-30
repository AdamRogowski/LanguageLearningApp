import os
from gtts import gTTS
from django.conf import settings


import os
from gtts import gTTS
from django.conf import settings

# Map your Language model's name to gTTS language codes
LANGUAGE_NAME_TO_GTTS = {
    "English": "en",
    "Polish": "pl",
    "Spanish": "es",
    "Danish": "da",
    # Add more as needed
}


def get_gtts_lang(language_obj):
    """Get gTTS language code from a Language model instance."""
    return LANGUAGE_NAME_TO_GTTS.get(language_obj.name, "en")  # Default to English


def generate_audio_file(text, language_obj, subdir, filename):
    """
    Generate an audio file for the given text and language.
    - language_obj: a Language model instance (e.g., word.lesson.prompt_language)
    """
    lang = get_gtts_lang(language_obj)
    audio_dir = os.path.join(settings.MEDIA_ROOT, subdir)
    os.makedirs(audio_dir, exist_ok=True)
    path = os.path.join(audio_dir, filename)
    if not os.path.exists(path):
        tts = gTTS(text, lang=lang)
        tts.save(path)
    return os.path.join(subdir, filename)  # relative to MEDIA_ROOT
