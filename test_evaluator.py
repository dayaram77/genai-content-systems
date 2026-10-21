from pathlib import Path

from evaluator import evaluate_lesson

lesson = Path("outputs/lesson.md").read_text(
    encoding="utf-8"
)

result = evaluate_lesson(lesson)

for check in result["checks"]:
    print(
        f'{check["id"]}: {check["status"]} '
        f'- {check["reason"]}'
    )

passed = all(
    check["status"] == "PASS"
    for check in result["checks"]
)

print("\nFinal decision:", "SHIP" if passed else "REJECT")
