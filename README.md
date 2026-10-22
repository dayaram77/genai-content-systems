# GenAI Content Systems: Self-Evolving Lesson Generator

## Overview

This project is a Generative AI-powered content system that creates beginner-friendly educational lessons and evaluates them against a predefined quality rubric.

The system uses Google's Gemini API to generate lessons, evaluate their quality, and improve rejected lessons through a feedback-driven regeneration loop.

The project demonstrates how Generative AI can be used to build a content generation and quality assurance workflow with automated evaluation, rejection logging, and controlled retries.

## Problem Statement

AI-generated educational content may contain factual inaccuracies, unexplained technical terminology, missing examples, or poor instructional structure.

This project addresses these challenges by introducing an evaluation and regeneration workflow that checks generated lessons against defined quality criteria before accepting them.

## Key Features

- **AI Lesson Generation:** Generates beginner-friendly lessons for a given topic.
- **Automated Evaluation:** Evaluates lessons against a configurable rubric.
- **Quality Checkpoints:** Checks accuracy, jargon, examples, coverage, and instructional flow.
- **Feedback-Driven Regeneration:** Uses failed checkpoints to guide lesson improvements.
- **Retry Control:** Limits regeneration to a maximum of two attempts.
- **Rejection Logging:** Saves rejected lessons and evaluation feedback.
- **Acceptance Workflow:** Saves the final lesson only when all rubric checkpoints pass.
- **Error Handling:** Separates temporary API or network failures from actual rubric rejection decisions.

## Technology Stack

- Python
- Google Gemini API
- Google GenAI Python SDK
- JSON for rubric configuration and evaluation results

## Project Structure

```text
genai-content-systems/
│
├── main.py
├── evaluator.py
├── test_retry_loop.py
├── evaluation/
│   └── rubric.json
├── outputs/
│   ├── accepted_lesson.json
│   ├── evaluation_1.json
│   ├── evaluation_2.json
│   └── rejection_1.json
│
├── .env
├── .gitignore
└── README.md
```

The `outputs/` directory contains generated lessons, evaluation results, and rejection logs. The exact files depend on the execution result.

## How It Works

The system follows a feedback-driven content generation pipeline:

1. A topic is provided to the lesson generator.
2. The generator creates an initial lesson.
3. The evaluator checks the lesson against the configured rubric.
4. If the lesson fails, the system records the failed checkpoints and rejection feedback.
5. The generator uses the previous lesson and failed checkpoints to create an improved version.
6. The regenerated lesson is evaluated again.
7. The system accepts the lesson when all checkpoints pass, or rejects it after reaching the maximum regeneration limit.

```text
Topic
  |
  v
Generate Lesson
  |
  v
Evaluate Against Rubric
  |
  v
All Checks Passed?
  |             |
 Yes             No
  |              |
  v              v
Accept Lesson   Record Rejection
                 |
                 v
           Regenerate Lesson
                 |
                 v
           Re-evaluate
```

## Evaluation Rubric

The lesson evaluator checks the following criteria:

| Checkpoint | Description |
|---|---|
| Accuracy | Verifies factual correctness of the lesson. |
| Jargon | Checks whether technical terminology is explained for beginners. |
| Example | Checks whether the lesson contains a concrete example. |
| Coverage | Checks whether the essential concepts are covered. |
| Flow | Checks whether the lesson follows a logical instructional structure. |

The rubric is configurable through `evaluation/rubric.json`.

## Example: Introduction to RAG

The retry-loop test uses the topic **Introduction to RAG**.

The initial lesson is deliberately incorrect:

> RAG is a model training method. It permanently changes the AI model whenever a user asks a question. RAG does not search documents.

The evaluator rejected this lesson because it failed the accuracy, jargon, example, coverage, and flow checkpoints.

The generator then used the failed checkpoints as feedback to regenerate the lesson.

### Test Result

The retry-loop test completed successfully:

- Initial decision: REJECT
- Failed checkpoints: 5
- Regeneration attempts: 1
- Final decision: ACCEPT

The accepted lesson was saved to `outputs/accepted_lesson.json`.

This result demonstrates that the system can detect an incorrect lesson, regenerate it using evaluation feedback, and accept a lesson after it passes the rubric.

## Installation and Setup

### Prerequisites

- Python 3.10 or a compatible Python version
- A Google Gemini API key
- Git

### 1. Clone the repository

```bash
git clone https://github.com/dayaram77/genai-content-systems.git
cd genai-content-systems
```

Replace `YOUR-USERNAME` with your GitHub username.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the packages used by the project:

```bash
pip install google-genai httpx python-dotenv
```

If a `requirements.txt` file is available, install from it instead:

```bash
pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Use your own API key. Do not commit the `.env` file or expose your API key in source code or public repositories.

## Running the Project

### Run the main application

```bash
python main.py
```

This runs the main lesson generation and evaluation workflow.

### Run the retry-loop test

```bash
python test_retry_loop.py
```

This runs the deliberately incorrect lesson through the evaluation and regeneration workflow.

The test demonstrates initial rejection, feedback-driven regeneration, re-evaluation, and final acceptance or rejection.

## Output Files

Depending on the execution result, the system may generate:

| File | Purpose |
|---|---|
| `evaluation_1.json` | Initial lesson evaluation. |
| `rejection_1.json` | Initial rejected lesson and failed checkpoints. |
| `generated_lesson_1.json` | First regenerated lesson. |
| `evaluation_2.json` | Evaluation of the first regenerated lesson. |
| `accepted_lesson.json` | Final accepted lesson and evaluation. |
| `final_rejection.json` | Final rejection after maximum regeneration attempts. |
| `api_error.json` | API/network error information when evaluation or generation cannot complete. |

API/network failures are logged separately and are not treated as rubric failures.

## Limitations

- Lesson quality depends on the Gemini model and the configured evaluation rubric.
- API availability, network connectivity, and usage limits may affect execution.
- Automated evaluation is not a substitute for human review of educational content.
- Regeneration is limited to two attempts to control repeated API calls.

## Future Improvements

- Add a web-based interface for lesson generation and evaluation.
- Support multiple educational topics and configurable lesson formats.
- Add human review and approval before publishing lessons.
- Improve evaluation consistency with additional test cases.
- Track quality scores across multiple generated lessons.

## Author

**Sable Dayaram**

GenAI Engineer

GitHub: (https://github.com/dayaram77)

## License

This project was developed as a GenAI engineering assessment. Add a license if you intend to distribute or reuse the project publicly.
