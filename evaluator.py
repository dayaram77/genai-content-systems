import json
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

client = genai.Client()

MODEL_NAME = "gemini-3.8-flash"

MAX_RETRIES = 3

RUBRIC_FILE = Path("evaluation/rubric.json")


# --------------------------------------------------
# Load rubric
# --------------------------------------------------

def load_rubric():
    """Load evaluation checkpoints from the rubric JSON."""

    if not RUBRIC_FILE.exists():
        raise FileNotFoundError(
            f"Rubric file not found: {RUBRIC_FILE}"
        )

    with RUBRIC_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


# --------------------------------------------------
# Gemini API with retry handling
# --------------------------------------------------

def generate_evaluation_with_retry(prompt):
    """Call Gemini and retry only temporary failures."""

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if not response.text:
                raise ValueError(
                    "Gemini returned an empty evaluation."
                )

            return response.text

        except ServerError as error:

            # Retry temporary server errors only.
            if error.code not in (500, 502, 503, 504):
                raise

            if attempt == MAX_RETRIES:
                raise

            wait_time = attempt * 5

            print(
                f"Evaluator server error {error.code}. "
                f"Retrying in {wait_time} seconds "
                f"({attempt}/{MAX_RETRIES})..."
            )

            time.sleep(wait_time)

        except httpx.TransportError:

            if attempt == MAX_RETRIES:
                raise

            wait_time = attempt * 3

            print(
                f"Network/API connection error. "
                f"Retrying in {wait_time} seconds "
                f"({attempt}/{MAX_RETRIES})..."
            )

            time.sleep(wait_time)

    raise RuntimeError("Evaluation failed after retries.")


# --------------------------------------------------
# Evaluate lesson
# --------------------------------------------------

def evaluate_lesson(lesson):
    """
    Evaluate a generated lesson using the rubric.

    Returns:
        {
            "checks": [
                {
                    "id": "accuracy",
                    "status": "PASS",
                    "reason": "..."
                }
            ]
        }
    """

    rubric = load_rubric()

    prompt = f"""
You are a strict evaluator for beginner-friendly AI lessons.

Evaluate the lesson against every checkpoint in the rubric.

RUBRIC:
{json.dumps(rubric, indent=2, ensure_ascii=False)}

LESSON:
{lesson}

Instructions:
1. Evaluate every rubric checkpoint independently.
2. Return PASS only if the lesson fully satisfies that checkpoint.
3. Return FAIL if a checkpoint is missing, inaccurate, misleading,
   or insufficiently explained.
4. Be strict about factual accuracy and beginner-friendliness.
5. Provide a concise reason for every decision.
6. Do not rewrite or improve the lesson.
7. Do not add checkpoints that are not in the rubric.

Return ONLY valid JSON in this exact structure:

{{
    "checks": [
        {{
            "id": "checkpoint_id",
            "status": "PASS or FAIL",
            "reason": "Explanation of the decision"
        }}
    ]
}}
"""

    print("Evaluating lesson against rubric...")

    response_text = generate_evaluation_with_retry(prompt)

    # Remove Markdown code fences if Gemini adds them.
    response_text = response_text.strip()

    if response_text.startswith("```"):
        lines = response_text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        response_text = "\n".join(lines).strip()

    try:
        evaluation = json.loads(response_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "Evaluator returned invalid JSON."
        ) from error

    # Validate expected output structure.
    if not isinstance(evaluation, dict):
        raise ValueError(
            "Evaluator response must be a JSON object."
        )

    if not isinstance(evaluation.get("checks"), list):
        raise ValueError(
            "Evaluator response must contain a checks list."
        )

    if not evaluation["checks"]:
        raise ValueError(
            "Evaluator returned no checkpoints."
        )

    # Validate each checkpoint.
    for check in evaluation["checks"]:

        if not isinstance(check, dict):
            raise ValueError(
                "Invalid checkpoint format."
            )

        if "id" not in check or "status" not in check:
            raise ValueError(
                "Checkpoint must contain id and status."
            )

        status = str(check["status"]).strip().upper()

        if status not in ("PASS", "FAIL"):
            raise ValueError(
                f"Invalid checkpoint status: {status}"
            )

        check["status"] = status

        if "reason" not in check:
            check["reason"] = "No reason provided."

    return evaluation
