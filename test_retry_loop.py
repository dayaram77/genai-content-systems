import json
from pathlib import Path

import httpx

from main import generate_lesson, get_failed_checks
from evaluator import evaluate_lesson


TOPIC = "Introduction to RAG"
MAX_REGENERATIONS = 2

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def save_json(file_path, data):
    """Save data as a formatted JSON file."""
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def save_api_error(stage, exc):
    """Save API/network errors separately from rubric decisions."""
    error_log = {
        "status": "API_ERROR",
        "topic": TOPIC,
        "stage": stage,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }

    error_path = OUTPUT_DIR / "api_error.json"
    save_json(error_path, error_log)

    print(f"\nAPI/network error during: {stage}")
    print(f"Error type: {type(exc).__name__}")
    print(f"Error details: {exc}")
    print(f"Error log saved to: {error_path}")
    print("No rubric decision was made for this step.")


def handle_api_error(stage, exc):
    """Log an API error and stop the test safely."""
    save_api_error(stage, exc)
    raise SystemExit(1)


# --------------------------------------------------
# 1. Deliberately incorrect lesson
# --------------------------------------------------

lesson = """
RAG is a model training method.
It permanently changes the AI model whenever a user asks a question.
RAG does not search documents.
"""

print("Evaluating the deliberately incorrect lesson...")

try:
    evaluation = evaluate_lesson(lesson)

except Exception as exc:
    handle_api_error("initial_evaluation", exc)


failed_checks = get_failed_checks(evaluation)

# Save the initial evaluation
save_json(
    OUTPUT_DIR / "evaluation_1.json",
    evaluation
)

# Save the initial rejection only if the evaluator rejected it
if failed_checks:

    save_json(
        OUTPUT_DIR / "rejection_1.json",
        {
            "topic": TOPIC,
            "lesson": lesson,
            "failed_checks": failed_checks,
            "evaluation": evaluation,
        },
    )

    print("\nInitial decision: REJECT")
    print("Failed checkpoints:")

    for check in failed_checks:
        print(f"- {check['id']}: {check['reason']}")

else:
    # The deliberately incorrect lesson unexpectedly passed.
    print("\nInitial decision: ACCEPT")
    print("The deliberately incorrect lesson passed the rubric.")

    save_json(
        OUTPUT_DIR / "accepted_lesson.json",
        {
            "topic": TOPIC,
            "lesson": lesson,
            "evaluation": evaluation,
            "regenerations": 0,
        },
    )

    raise SystemExit(0)


# --------------------------------------------------
# 2. Regeneration and re-evaluation
# --------------------------------------------------

for attempt in range(1, MAX_REGENERATIONS + 1):

    print(f"\nRegeneration attempt {attempt}/{MAX_REGENERATIONS}")

    # Generate an improved lesson
    try:
        lesson = generate_lesson(
            topic=TOPIC,
            previous_lesson=lesson,
            failed_checks=failed_checks,
        )

    except Exception as exc:
        handle_api_error(
            f"lesson_generation_attempt_{attempt}",
            exc,
        )

    # Save the generated lesson for recovery/debugging
    save_json(
        OUTPUT_DIR / f"generated_lesson_{attempt}.json",
        {
            "topic": TOPIC,
            "lesson": lesson,
            "attempt": attempt,
            "previous_failed_checks": failed_checks,
        },
    )

    print("\nEvaluating regenerated lesson...")

    # Evaluate the regenerated lesson
    try:
        evaluation = evaluate_lesson(lesson)

    except Exception as exc:
        handle_api_error(
            f"lesson_evaluation_attempt_{attempt}",
            exc,
        )

    failed_checks = get_failed_checks(evaluation)

    evaluation_number = attempt + 1

    # Save this evaluation
    save_json(
        OUTPUT_DIR / f"evaluation_{evaluation_number}.json",
        evaluation,
    )

    # --------------------------------------------------
    # 3. ACCEPT if every checkpoint passes
    # --------------------------------------------------

    if not failed_checks:

        print("\nFinal decision: ACCEPT")
        print("All checkpoints passed.")

        save_json(
            OUTPUT_DIR / "accepted_lesson.json",
            {
                "topic": TOPIC,
                "lesson": lesson,
                "evaluation": evaluation,
                "regenerations": attempt,
            },
        )

        print(
            "\nAccepted lesson saved to "
            "outputs/accepted_lesson.json"
        )

        break

    # --------------------------------------------------
    # 4. REJECT if checkpoints still fail
    # --------------------------------------------------

    save_json(
        OUTPUT_DIR / f"rejection_{evaluation_number}.json",
        {
            "topic": TOPIC,
            "lesson": lesson,
            "failed_checks": failed_checks,
            "evaluation": evaluation,
        },
    )

    print("\nLesson still rejected.")
    print("Failed checkpoints:")

    for check in failed_checks:
        print(f"- {check['id']}: {check['reason']}")

else:

    # --------------------------------------------------
    # 5. Final rejection after maximum attempts
    # --------------------------------------------------

    print("\nFinal decision: REJECT")
    print("Maximum regeneration attempts reached.")

    save_json(
        OUTPUT_DIR / "final_rejection.json",
        {
            "topic": TOPIC,
            "last_lesson": lesson,
            "failed_checks": failed_checks,
            "evaluation": evaluation,
            "regenerations": MAX_REGENERATIONS,
        },
    )

    print(
        "\nFinal rejection saved to "
        "outputs/final_rejection.json"
    )
