import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Story Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"


class PromptRequest(BaseModel):
    prompt: str = Field(..., max_length=200)


class StoryResponse(BaseModel):
    story: str or None = None


@app.post("/generate", response_model=StoryResponse)
async def generate_story(data: PromptRequest):
    if not data.prompt:
        raise HTTPException(status_code=400, detail="prompt обязателен")

    # Системный промпт: задаём роль модели
    system_prompt = (
        "посчитай: "
    )

    full_prompt = f"{system_prompt}{data.prompt}"

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": full_prompt,
                    "stream": False,       # ждём весь ответ целиком
                    "options": {
                        "temperature": 0.8,   # креативность
                        "num_predict": 500,   # лимит токенов в ответе
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
            detail="Модель слишком долго генерировала ответ. Попробуй уменьшить prompt или num_predict.",
        )
