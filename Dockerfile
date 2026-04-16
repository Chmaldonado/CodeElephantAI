FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY tutor_agent ./tutor_agent
COPY data ./data

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

CMD ["python", "-m", "tutor_agent.main", "chat", "--user-id", "learner"]
