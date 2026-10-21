import json
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

from evaluator import evaluate_lesson


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

client = genai.Client()

MODEL_NAME = "gemini-3.8-flash"

MAX_RETRIES = 3
MAX_REGENERATIONS = 2

OUTPUT_DIR = Path("outputs")
MEMORY_FILE = Path("memory.json")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# File utilities
# --------------------------------------------------

def save_json(file_path, data):
    """Save data to a JSON file."""

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def load_memory():
    """Load persistent memory from JSON."""

    if not MEMORY_FILE.exists():
        return {
            "topic": "Introduction to RAG",
            "last_accepted_lesson": None,
            "last_failed_checks": [],
            "generation_count": 0
        }

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            memory = json.load(file)

        return memory

    except (json.JSONDecodeError, OSError):
        print("Warning: Memory file could not be read.")
        return {
            "topic": "Introduction to RAG",
            "last_accepted_lesson": None,
            "last_failed_checks": [],
            "generation_count": 0
        }


def save_memory(memory):
    """Persist memory."""

    save_json(MEMORY_FILE, memory)


# --------------------------------------------------
# Gemini API with retry handling
# --------------------------------------------------

def generate_with_retry(prompt):
    """
    Generate content using Gemini.

    Retries temporary API and network errors.
    """

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if not response.text:
                raise ValueError(
                    "Gemini returned an empty response."
                )

            return response.text

        except ServerError as error:

            # Retry temporary server errors only.
            if error.code not in (500, 502, 503, 504):
                raise

            if attempt == MAX_RETRIES:
                raise

            wait_time = attempt * 10

            print(
                f"Gemini server error {error.code}. "
                f"Retrying in {wait_time} seconds "
                f"({attempt}/{MAX_RETRIES})..."
            )

            time.sleep(wait_time)

        except httpx.TransportError:

            if attempt == MAX_RETRIES:
                raise

            wait_time = attempt * 10

            print(
                f"Network error. Retrying in "
                f"{wait_time} seconds "
                f"({attempt}/{MAX_RETRIES})..."
            )

            time.sleep(wait_time)

    raise RuntimeError("Gemini generation failed.")


# --------------------------------------------------
# Lesson generation
# --------------------------------------------------

def generate_lesson(topic, previous_lesson=None, failed_checks=None):
    """
    Generate a beginner-friendly lesson.

    If a previous lesson failed evaluation, regenerate it
    while addressing the failed checkpoints.
    """

    if failed_checks is None:
        failed_checks = []

    if previous_lesson and failed_checks:

        failed_check_text = "\n".join(
            f"- {check['id']}: {check['reason']}"
            for check in failed_checks
        )

        prompt = f"""
You are an expert AI educator.

Improve the following lesson about "{topic}".

The previous lesson failed these evaluation checkpoints:
{failed_check_text}

Previous lesson:
{previous_lesson}

Requirements:
1. Correct all failed checkpoints.
2. Explain concepts for a complete beginner.
3. Use simple English.
4. Explain technical terms when introduced.
5. Include a practical example.
6. Cover the important concepts of the topic.
7. Maintain a logical flow.
8. Do not mention the evaluation process.
9. Return only the complete improved lesson.
"""

    else:

        prompt = f"""
You are an expert AI educator.

Create a beginner-friendly lesson about "{topic}".

Requirements:
1. Start with a simple introduction.
2. Explain what the topic means.
3. Explain why it is useful.
4. Explain the important concepts step by step.
5. Use simple English.
6. Explain technical terms when introduced.
7. Include a practical example.
8. Include a short summary at the end.
9. Keep the lesson logically organized.
10. Do not assume the learner has prior knowledge.

Return only the complete lesson.
"""

    return generate_with_retry(prompt)


# --------------------------------------------------
# Evaluation utilities
# --------------------------------------------------

def get_failed_checks(evaluation):
    """Return checkpoints that failed evaluation."""

    failed_checks = []

    for check in evaluation.get("checks", []):

        status = check.get("status", "").strip().upper()

        if status != "PASS":
            failed_checks.append({
                "id": check.get("id", "unknown"),
                "status": status,
                "reason": check.get(
                    "reason",
                    "No reason provided."
                )
            })

    return failed_checks


def print_evaluation(evaluation):
    """Display evaluation results."""

    print("\nEvaluation results")
    print("-" * 40)

    checks = evaluation.get("checks", [])

    if not checks:
        print("No evaluation checkpoints returned.")
        return

    for check in checks:

        checkpoint_id = check.get("id", "unknown")
        status = check.get("status", "UNKNOWN")
        reason = check.get("reason", "")

        print(f"{checkpoint_id}: {status}")
        print(f"Reason: {reason}\n")


def evaluation_passed(evaluation):
    """Return True only when all checkpoints pass."""

    checks = evaluation.get("checks", [])

    if not checks:
        return False

    return all(
        check.get("status", "").strip().upper() == "PASS"
        for check in checks
    )


# --------------------------------------------------
# Main workflow
# --------------------------------------------------

def main():

    topic = "Introduction to RAG"

    memory = load_memory()

    previous_lesson = None
    failed_checks = []

    print("=" * 60)
    print("GENAI CONTENT SYSTEM")
    print("=" * 60)

    print(f"\nTopic: {topic}")

    print("\nGenerating lesson...")

    for generation in range(MAX_REGENERATIONS + 1):

        try:

            lesson = generate_lesson(
                topic=topic,
                previous_lesson=previous_lesson,
                failed_checks=failed_checks
            )

        except Exception as error:

            print("\nLesson generation failed.")
            print(f"Error: {error}")

            save_json(
                OUTPUT_DIR / "api_error.json",
                {
                    "topic": topic,
                    "error": str(error),
                    "generation_attempt": generation + 1
                }
            )

            return

        memory["generation_count"] = (
            memory.get("generation_count", 0) + 1
        )

        print("\nLesson generated successfully.")

        # Save the most recent generated lesson.
        save_json(
            OUTPUT_DIR / "latest_lesson.json",
            {
                "topic": topic,
                "generation": generation + 1,
                "lesson": lesson
            }
        )

        print("\nEvaluating lesson...")

        try:

            evaluation = evaluate_lesson(lesson)

        except Exception as error:

            print("\nLesson evaluation failed.")
            print(f"Error: {error}")

            save_json(
                OUTPUT_DIR / "evaluation_error.json",
                {
                    "topic": topic,
                    "error": str(error),
                    "generation_attempt": generation + 1
                }
            )

            return

        print_evaluation(evaluation)

        # Save every evaluation result.
        save_json(
            OUTPUT_DIR / f"evaluation_{generation + 1}.json",
            evaluation
        )

        # If every checkpoint passes, accept the lesson.
        if evaluation_passed(evaluation):

            print("\n" + "=" * 60)
            print("LESSON ACCEPTED")
            print("=" * 60)

            save_json(
                OUTPUT_DIR / "accepted_lesson.json",
                {
                    "topic": topic,
                    "lesson": lesson,
                    "evaluation": evaluation,
                    "generation": generation + 1
                }
            )

            memory["topic"] = topic
            memory["last_accepted_lesson"] = lesson
            memory["last_failed_checks"] = []

            save_memory(memory)

            print("\nAccepted lesson saved to:")
            print(OUTPUT_DIR / "accepted_lesson.json")

            print("\nMemory updated:")
            print(MEMORY_FILE)

            return

        # If evaluation fails, prepare for regeneration.
        failed_checks = get_failed_checks(evaluation)

        print("\nLesson rejected.")

        save_json(
            OUTPUT_DIR / f"rejection_{generation + 1}.json",
            {
                "topic": topic,
                "lesson": lesson,
                "failed_checks": failed_checks,
                "evaluation": evaluation
            }
        )

        previous_lesson = lesson

        memory["topic"] = topic
        memory["last_failed_checks"] = failed_checks

        save_memory(memory)

        # Do not exceed the regeneration limit.
        if generation < MAX_REGENERATIONS:

            print(
                f"\nRegenerating lesson "
                f"({generation + 1}/{MAX_REGENERATIONS})..."
            )

        else:

            print("\nMaximum regeneration attempts reached.")

            save_json(
                OUTPUT_DIR / "final_rejection.json",
                {
                    "topic": topic,
                    "last_lesson": lesson,
                    "failed_checks": failed_checks,
                    "evaluation": evaluation,
                    "regenerations": MAX_REGENERATIONS
                }
            )

            print("\nFinal rejection saved to:")
            print(OUTPUT_DIR / "final_rejection.json")

            return


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
