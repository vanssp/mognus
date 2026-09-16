from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Story Generator API")

print(1)

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
    story: str


@app.post("/generate", response_model=StoryResponse)
def generate_story(data: PromptRequest):
    # Здесь позже подключишь настоящую генерацию (LLM и т.д.)
    generated = f"Сгенерированная история по промпту: «{data.prompt}»"
    return StoryResponse
