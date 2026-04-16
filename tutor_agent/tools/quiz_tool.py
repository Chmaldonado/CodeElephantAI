from __future__ import annotations

from tutor_agent.llm import LocalLLM


class GenerateQuizTool:
    name = "generate_quiz"
    description = "Generates short coding quizzes tailored to topic and difficulty."

    def __init__(self, llm: LocalLLM):
        self.llm = llm

    def __call__(self, topic: str, difficulty: str = "medium") -> dict:
        prompt = (
            "Create a concise coding quiz in JSON with keys: "
            "title, questions (array of objects with question, answer, hint). "
            f"Topic: {topic}. Difficulty: {difficulty}. Keep 3 questions."
        )
        return self.llm.chat_json(
            system_prompt="You are a helpful coding quiz generator.",
            user_prompt=prompt,
        )
