from evaluator import evaluate_lesson

bad_lesson = """
# Introduction to RAG

RAG means Retrieval-Augmented Generation.

RAG is a model training method.
It permanently changes the AI model by adding new information.

For example, if you ask a chatbot about your school's
holiday dates, RAG does not search any documents.
It simply guesses the answer.

RAG is useful because it makes AI faster.
"""

print("Testing evaluator with an intentionally incorrect lesson...")

result = evaluate_lesson(bad_lesson)

for check in result["checks"]:
    print(
        f'{check["id"]}: {check["status"]} '
        f'- {check["reason"]}'
    )

failed = [
    check for check in result["checks"]
    if check["status"].strip().upper() != "PASS"
]

print("\nFinal decision:", "REJECT" if failed else "SHIP")
