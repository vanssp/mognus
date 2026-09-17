from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Story Generator API")

# Разрешаем запросы с фронтенда (Vite по умолчанию на 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptRequest(BaseModel):
    prompt: str = Field(..., max_length=200)


class StoryResponse(BaseModel):
    # Правильный способ сделать поле необязательным (Python 3.10+)
    story: str or None = None


@app.post("/generate", response_model=StoryResponse)
def generate_story(data: PromptRequest):
    if not data.prompt:
        raise HTTPException(status_code=400, detail="prompt обязателен")

    generated = f"Сгенерированная история по промпту: «{data.prompt}»"
    # Возвращаем ЭКЗЕМПЛЯР, передавая значение в поле story
    return StoryResponse(story=generated)
