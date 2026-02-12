"""Practice session views: handling learning practice flow."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import difflib
from Levenshtein import distance

from ..models import UserLesson, UserWord, UserDirectory
from ..utils_practice_session import (
    PRACTICE_MODES,
    get_practice_session_keys,
    initialize_practice_session,
    get_question_and_answer,
)


@login_required(login_url="login")
def start_practice(request, user_lesson_id, mode="normal"):
    """Initialize and start a practice session."""
    user_lesson = get_object_or_404(UserLesson, id=user_lesson_id, user=request.user)

    # Check if there are any words that still need practice
    words_to_practice = UserWord.objects.filter(
        user_lesson=user_lesson, current_progress__lt=user_lesson.target_progress
    ).exists()

    if not words_to_practice:
        messages.info(
            request,
            "Target progress has been reached for all words! Consider resetting progress or increasing target progress in Edit lesson settings."
        )
        return redirect("my-lesson-details", my_lesson_id=user_lesson_id)

    initialize_practice_session(request, user_lesson, mode)
    return redirect("practice", user_lesson_id=user_lesson_id, mode=mode)


@login_required(login_url="login")
def practice(request, user_lesson_id, mode="normal"):
    """Main practice view - present question to user."""
    window_key, pool_key, answer_key = get_practice_session_keys(user_lesson_id, mode)
    window = request.session.get(window_key, [])
    pool = request.session.get(pool_key, [])

    if not window:
        # Session complete
        request.session.pop(window_key, None)
        request.session.pop(pool_key, None)
        request.session.pop(answer_key, None)
        messages.info(request, "Practice session completed!")
        return redirect("my-lesson-details", my_lesson_id=user_lesson_id)

    user_word = get_object_or_404(
        UserWord,
        id=window[0],
        user_lesson__user=request.user,
        user_lesson_id=user_lesson_id,
    )

    question, correct_answer = get_question_and_answer(user_word, mode)

    if request.method == "POST":
        answer = request.POST.get("answer", "").strip()
        lev_distance = distance(answer.lower(), correct_answer.lower())
        correct = lev_distance < user_word.user_lesson.allowed_error_margin + 1
        diff_html = (
            highlight_differences(answer, correct_answer) if lev_distance != 0 else ""
        )
        request.session[answer_key] = {
            "user_word_id": user_word.id,
            "answer": answer,
            "correct": correct,
            "correct_answer": correct_answer,
            "diff_html": diff_html,
            "lev_distance": lev_distance,
        }
        return redirect("practice-feedback", user_lesson_id=user_lesson_id, mode=mode)

    # Get breadcrumb path from lesson's directory
    current_directory = user_word.user_lesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    return render(
        request,
        "base/authenticated/my_lessons/practice/practice.html",
        {
            "user_word": user_word,
            "user_lesson": user_word.user_lesson,
            "user_lesson_id": user_lesson_id,
            "question": question,
            "mode": mode,
            "breadcrumb_path": breadcrumb_path,
            "breadcrumb_lesson": user_word.user_lesson,
        },
    )


@login_required(login_url="login")
def practice_feedback(request, user_lesson_id, mode="normal"):
    """Show feedback after user submits an answer."""
    window_key, pool_key, answer_key = get_practice_session_keys(user_lesson_id, mode)
    window = request.session.get(window_key, [])
    pool = request.session.get(pool_key, [])
    answer_data = request.session.get(answer_key)

    if not answer_data or not window:
        return redirect("practice", user_lesson_id=user_lesson_id, mode=mode)

    user_word = get_object_or_404(
        UserWord,
        id=answer_data["user_word_id"],
        user_lesson__user=request.user,
        user_lesson_id=user_lesson_id,
    )

    if request.method == "POST":
        if answer_data["correct"] or "accept_as_correct" in request.POST:
            user_word.current_progress += 1
            user_word.save()
            window.pop(0)
            if pool:
                window.append(pool.pop(0))
        else:
            user_word.current_progress = max(0, user_word.current_progress - 1)
            user_word.save()
            word_id = window.pop(0)
            window.append(word_id)
        request.session[window_key] = window
        request.session[pool_key] = pool
        request.session.pop(answer_key, None)
        return redirect("practice", user_lesson_id=user_lesson_id, mode=mode)

    # Get breadcrumb path from lesson's directory
    current_directory = user_word.user_lesson.directory
    if not current_directory:
        current_directory = UserDirectory.get_or_create_root_directory(request.user)
    breadcrumb_path = current_directory.get_path()

    # Get the original question for display
    question, _ = get_question_and_answer(user_word, mode)

    context = {
        "user_word": user_word,
        "user_lesson": user_word.user_lesson,
        "user_lesson_id": user_lesson_id,
        "question": question,
        "answer": answer_data["answer"],
        "correct": answer_data["correct"],
        "diff_html": answer_data.get("diff_html", ""),
        "lev_distance": answer_data.get("lev_distance", ""),
        "mode": mode,
        "breadcrumb_path": breadcrumb_path,
        "breadcrumb_lesson": user_word.user_lesson,
    }
    return render(request, "base/authenticated/my_lessons/practice/practice_feedback.html", context)


@login_required(login_url="login")
def cancel_practice(request, user_lesson_id):
    """Cancel the current practice session."""
    # Cancel all possible practice sessions for this lesson (all modes)
    for mode in PRACTICE_MODES:
        window_key, pool_key, answer_key = get_practice_session_keys(
            user_lesson_id, mode
        )
        request.session.pop(window_key, None)
        request.session.pop(pool_key, None)
        request.session.pop(answer_key, None)
    messages.info(request, "Practice session cancelled.")
    return redirect("my-lesson-details", my_lesson_id=user_lesson_id)


def highlight_differences(user_answer, correct_answer):
    """Return HTML with mismatches highlighted."""
    from django.utils.html import escape
    matcher = difflib.SequenceMatcher(None, user_answer, correct_answer)
    result = []
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == "equal":
            result.append(escape(correct_answer[b0:b1]))
        else:
            # Highlight mismatched parts from the correct answer (escape to prevent XSS)
            result.append(f'<span class="diff">{escape(correct_answer[b0:b1])}</span>')
    return "".join(result)
