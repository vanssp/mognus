package ru.mognu.app.data

import android.content.Context
import org.json.JSONArray

data class Question(
    val id: Int,
    val nameA: String,
    val nameB: String,
    val winner: String,
    val explanation: String,
    val imageA: String,
    val imageB: String,
) {
    fun isCorrect(side: String): Boolean = side == winner
}

object QuestionRepository {
    fun load(context: Context): List<Question> {
        val text = context.assets.open("questions.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
        val array = JSONArray(text)
        return List(array.length()) { index ->
            val item = array.getJSONObject(index)
            Question(
                id = item.getInt("id"),
                nameA = item.getString("nameA"),
                nameB = item.getString("nameB"),
                winner = item.getString("winner"),
                explanation = item.getString("explanation"),
                imageA = item.getString("imageA"),
                imageB = item.getString("imageB"),
            )
        }
    }
}
