import { useState } from "react";

const MAX_LENGTH = 200;
const API_URL = "/api/generate";

// Список запрещённых слов (можно менять/дополнять)
const BLOCKED_WORDS = [
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
];

function App() {
  const [prompt, setPrompt] = useState("");
  const [story, setStory] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Проверяем, есть ли в тексте запрещённые слова (регистронезависимо)
  const hasBlockedWord = prompt.toLowerCase().split(/\s+/).some(word =>
    BLOCKED_WORDS.includes(word.replace(/[^\w]/g, ""))
  );

  const handleGenerate = async () => {
    if (!prompt.trim() || hasBlockedWord) return;

    setLoading(true);
    setStory("");
    setErrorMsg("");

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Ошибка сервера");
      }

      setStory(data.story);
    } catch (err) {
      setStory("Ошибка при обращении к серверу.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Что ты сегодня съел:</h1>

      <textarea
        value={prompt}
        maxLength={MAX_LENGTH}
        onChange={(e) => {
          const value = e.target.value;
          setPrompt(value);
          // Сбрасываем ошибку при редактировании
          if (hasBlockedWord && !value.toLowerCase().split(/\s+/).some(w =>
            BLOCKED_WORDS.includes(w.replace(/[^\w]/g, ""))
          )) {
            setErrorMsg("");
          }
        }}
        placeholder="Например: Куриное филе варёное 100 грамм"
      />

      <div className="counter">
        {prompt.length} / {MAX_LENGTH}
      </div>

      {hasBlockedWord && (
        <div className="error-message" style={{ color: "red", marginBottom: "8px" }}>
          В тексте есть запрещённые слова — отправка невозможна.
        </div>
      )}

      <button
        onClick={handleGenerate}
        disabled={loading || !prompt.trim() || hasBlockedWord}
        style={{ opacity: loading || !prompt.trim() || hasBlockedWord ? 0.6 : 1 }}
      >
        {loading ? "Подсчет КБЖУ..." : "Посчитать КБЖУ"}
      </button>

      {story && <div className="result">{story}</div>}
    </div>
  );
}

export default App;
