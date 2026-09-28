import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Story Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "qwen2.5:1.5b"


class PromptRequest(BaseModel):
    prompt: str = Field(..., max_length=500)


class StoryResponse(BaseModel):
    story: Optional[str] = None


@app.post("/generate", response_model=StoryResponse)
async def generate_story(data: PromptRequest):
    if not data.prompt:
        raise HTTPException(status_code=400, detail="prompt обязателен")

    broken_words = [
        "член",
        "хуй",
        "минет",
        "киска",
        "сосать",
        "лизать",
        "очко",
        "жопа",
        "попа",
        "блядь",
        "блять",
        "ебля",
        "ебаться",
        "говно",
        "гамно",
        "какашки",
        "кал",
        "секс",
        "взломать",
        "hack",
        "sql",
        "delete",
        "drop",
        "admin",
        "пароль",
        "password",
        "token",
        "ключ",
        "secret",
        "root",
        "sudo",
        "rm",
        "format",
        "virus",
        "malware"
    ]
    for w in broken_words:
        if w in data.prompt:
            raise HTTPException(status_code=403, detail="Запрещенные слова использовать нельзя...")

    system_prompt = (
        "Распознай продукты и их вес, затем рассчитай каллории, белки, жиры и углеводы. "
        "Отвечай коротко на русском. Формат ответа:\n"
        "Продукт — вес — калории — Б/Ж/У. в конце выводи общую сумму КБЖУ:"
    )

    full_prompt = f"{system_prompt}\n\n{data.prompt}"

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,     # меньше фантазии — точнее расчёты
                        "num_predict": 512,      # 512 токенов хватает для КБЖУ
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,   # не повторяет одно и то же
                    },
                },
            )
            response.raise_for_status()

        result = response.json()
        generated_text = result.get("response", "").strip()

        if not generated_text:
            raise HTTPException(status_code=500, detail="Модель вернула пустой ответ")

        return StoryResponse(story=generated_text)

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Не удалось подключиться к Ollama. Проверь, что контейнер mog-ollama запущен.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama вернула ошибку: {e.response.text}",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Модель слишком долго генерировала ответ. Попробуй уменьшить prompt.",
        )
