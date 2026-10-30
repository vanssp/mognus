package ru.mognu.app

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import ru.mognu.app.ads.YandexInterstitial
import ru.mognu.app.audio.GameFeedback
import ru.mognu.app.data.ProgressStore
import ru.mognu.app.data.QuestionRepository
import ru.mognu.app.ui.EndScreen
import ru.mognu.app.ui.LaunchScreen
import ru.mognu.app.ui.MognuTheme
import ru.mognu.app.ui.PlayScreen
import ru.mognu.app.ui.Screen

class MainActivity : AppCompatActivity() {
    private lateinit var feedback: GameFeedback
    private lateinit var ads: YandexInterstitial

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        feedback = GameFeedback(this)
        ads = YandexInterstitial(this)
        ads.preload()
        val questions = QuestionRepository.load(this)
        val progress = ProgressStore(this)
        setContent {
            MognuTheme {
                val total = questions.size
                var solved by remember { mutableIntStateOf(progress.solved().coerceAtMost(total)) }
                var screen by remember {
                    mutableStateOf(if (total > 0 && solved >= total) Screen.End else Screen.Launch)
                }
                var revealed by remember(solved) { mutableStateOf(false) }
                var accepted by remember(solved) { mutableStateOf(false) }
                var locked by remember { mutableStateOf(false) }

                fun finishQuestion() {
                    if (locked || total == 0) return
                    locked = true
                    val next = (solved + 1).coerceAtMost(total)
                    progress.setSolved(next)
                    val go = {
                        solved = next
                        locked = false
                        screen = if (next >= total) Screen.End else Screen.Play
                    }
                    if (next % 10 == 0) ads.showThen(go) else go()
                }

                when (screen) {
                    Screen.Launch -> LaunchScreen(solved = solved, total = total) {
                        screen = if (total == 0 || solved >= total) Screen.End else Screen.Play
                    }
                    Screen.End -> EndScreen()
                    Screen.Play -> {
                        val question = questions[solved.coerceIn(0, total - 1)]
                        PlayScreen(
                            question = question,
                            solved = solved + 1,
                            total = total,
                            revealed = revealed,
                            onPick = { side ->
                                if (locked || accepted) return@PlayScreen
                                if (question.isCorrect(side)) {
                                    accepted = true
                                    feedback.win()
                                    finishQuestion()
                                } else {
                                    feedback.miss()
                                    revealed = true
                                }
                            },
                            onNext = {
                                if (locked || accepted) return@PlayScreen
                                accepted = true
                                finishQuestion()
                            },
                        )
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        if (::ads.isInitialized) ads.destroy()
        if (::feedback.isInitialized) feedback.release()
        super.onDestroy()
    }
}
