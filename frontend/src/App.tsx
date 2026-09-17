import { useState } from "react";

const MAX_LENGTH = 200;
const API_URL = "/api/generate";

function App() {
  const [prompt, setPrompt] = useState("");
  const [story, setStory] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setStory("");
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      setStory(data.story);
    } catch (err) {
      setStory("Ошибка при обращении к серверу.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Введите промпт для истории</h1>
      <textarea
        value={prompt}
        maxLength={MAX_LENGTH}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Например: история о космонавте, застрявшем на Марсе"
      />
      <div className="counter">
        {prompt.length} / {MAX_LENGTH}
      </div>
      <button onClick={handleGenerate} disabled={loading || !prompt.trim()}>
        {loading ? "Генерация..." : "Сгенерировать"}
      </button>
      {story && <div className="result">{story}</div>}
    </div>
  );
}

export default App;