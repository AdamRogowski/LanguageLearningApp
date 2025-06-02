from random import shuffle
from .models import UserWord

PRACTICE_MODES = {
    "normal": 0,
    "reverse": 1,
    # Add more modes as needed
}


def get_mode_from_str(mode_str):
    return PRACTICE_MODES.get(mode_str, 0)


def get_practice_session_keys(user_lesson_id, mode):
    prefix = f"practice_{mode}_{user_lesson_id}"
    return (f"{prefix}_window", f"{prefix}_pool", f"{prefix}_answer")


def initialize_practice_session(request, user_lesson, mode):
    window_key, pool_key, answer_key = get_practice_session_keys(user_lesson.id, mode)
    # Clear all possible practice sessions for this lesson
    for m in PRACTICE_MODES:
        w, p, a = get_practice_session_keys(user_lesson.id, m)
        request.session.pop(w, None)
        request.session.pop(p, None)
        request.session.pop(a, None)

    user_words = list(
        UserWord.objects.filter(
            user_lesson=user_lesson, current_progress__lt=user_lesson.target_progress
        ).values_list("id", flat=True)
    )

    shuffle(user_words)
    window = user_words[: user_lesson.practice_window]
    pool = user_words[user_lesson.practice_window :]
    request.session[window_key] = window
    request.session[pool_key] = pool


def get_question_and_answer(user_word, mode):
    if mode == "reverse":
        question = user_word.word.prompt
        correct_answer = user_word.word.translation.strip()
    else:  # normal
        question = user_word.word.translation
        correct_answer = user_word.word.prompt.strip()
    return question, correct_answer
