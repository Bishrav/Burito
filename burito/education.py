"""Explicit home education. Answers never leave local memory."""

from .memory import Memory


QUESTIONS = (
    ("name", "What should Burito call you?"),
    ("language", "Which languages should Burito use with you?"),
    ("communication", "How should Burito explain things to you?"),
    ("goal", "What is one goal you want Burito to help with?"),
    ("interest", "What is one interest you want Burito to remember?"),
)


def teach(memory=None):
    memory = memory if memory is not None else Memory()
    print("Teach Burito about you. Each answer is saved locally as a fact you supplied.")
    print("Enter skips a question. Ctrl+C stops; earlier answers remain saved.")
    saved = 0
    try:
        for category, question in QUESTIONS:
            answer = input(question + " ").strip()
            if answer:
                identifier = memory.remember(answer, source=f"owner onboarding: {category}")
                saved += 1
                print(f"Saved: {identifier}")
    except (EOFError, KeyboardInterrupt):
        print("\nEducation stopped.")
    print(f"Saved {saved} fact(s). Use 'memories' to inspect or 'correct' to change them.")
    return saved
