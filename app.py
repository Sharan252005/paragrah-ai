import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))

app = FastAPI(title="Smart Study Notes Generator")
WORD_PATTERN = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
INDEX_FILE = Path(__file__).with_name("index.html")


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


def word_count(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def make_result(text: str, summary: str, key_points: list[str]) -> dict[str, Any]:
    original_count = word_count(text)
    summary_count = word_count(summary)
    reduction = (
        round((original_count - summary_count) / original_count * 100, 1)
        if original_count
        else 0.0
    )
    return {
        "summary": summary,
        "key_points": key_points,
        "original_word_count": original_count,
        "summary_word_count": summary_count,
        "reduction_percentage": reduction,
    }


def generate_notes(text: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="The AI service is not configured. Add OPENAI_API_KEY to the deployment environment.",
        )

    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You create accurate study notes from text. Return only a JSON object "
                    'with a concise 1-2 sentence "summary" and a "key_points" array of '
                    "3-5 concise strings. Preserve the source meaning and do not add facts."
                ),
            },
            {"role": "user", "content": text},
        ],
    }
    request = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            completion = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise HTTPException(
                status_code=503,
                detail="The AI service is busy or its usage limit was reached. Please try again later.",
            ) from error
        if error.code == 401:
            raise HTTPException(
                status_code=502,
                detail="The AI service rejected the API key. Check that OPENAI_API_KEY is valid and active.",
            ) from error
        if error.code == 404:
            raise HTTPException(
                status_code=502,
                detail="The configured AI model was not found. Check the OPENAI_MODEL setting.",
            ) from error
        raise HTTPException(
            status_code=502,
            detail="The AI service rejected the request. Check the API key and model configuration.",
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to the AI service. Please try again.",
        ) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=502,
            detail="The AI service returned an invalid response.",
        ) from error

    try:
        content = completion["choices"][0]["message"]["content"]
        notes = json.loads(content)
        summary = notes["summary"]
        key_points = notes["key_points"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=502,
            detail="The AI service returned notes in an unexpected format.",
        ) from error

    if (
        not isinstance(summary, str)
        or not summary.strip()
        or not isinstance(key_points, list)
        or not 3 <= len(key_points) <= 5
        or any(not isinstance(point, str) or not point.strip() for point in key_points)
    ):
        raise HTTPException(
            status_code=502,
            detail="The AI service returned incomplete study notes. Please try again.",
        )

    return make_result(text, summary.strip(), [point.strip() for point in key_points])


@app.get("/")
def home() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.post("/api/generate")
def generate(request: GenerateRequest) -> dict[str, Any]:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Enter a paragraph to generate study notes.")
    if not word_count(text):
        raise HTTPException(status_code=422, detail="Enter text that contains at least one word.")
    return generate_notes(text)
