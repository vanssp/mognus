package ru.mognu.app.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.SoundPool
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

/**
 * Short original tones. Playback follows the music stream, so a muted or
 * zero-volume device stays silent and does not throw.
 */
class GameFeedback(context: Context) {
    private val app = context.applicationContext
    private val audio = app.getSystemService(AudioManager::class.java)
    private val vibrator: Vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        app.getSystemService(VibratorManager::class.java).defaultVibrator
    } else {
        @Suppress("DEPRECATION")
        app.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
    }
    private val pool: SoundPool
    private var winId = 0
    private var missId = 0

    init {
        val attrs = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_GAME)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()
        pool = SoundPool.Builder().setMaxStreams(2).setAudioAttributes(attrs).build()
        winId = load("sounds/win.ogg")
        missId = load("sounds/miss.ogg")
    }

    fun win() = play(winId)

    fun miss() {
        play(missId)
        vibrate()
    }

    fun release() {
        pool.release()
    }

    private fun load(path: String): Int {
        return try {
            app.assets.openFd(path).use { descriptor -> pool.load(descriptor, 1) }
        } catch (_: Exception) {
            0
        }
    }

    private fun play(soundId: Int) {
        if (soundId == 0) return
        try {
            val max = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            val volume = if (max <= 0) {
                0f
            } else {
                audio.getStreamVolume(AudioManager.STREAM_MUSIC).toFloat() / max.toFloat()
            }
            pool.play(soundId, volume, volume, 1, 0, 1f)
        } catch (_: Exception) {
            // A muted stream or a missing device must not crash the game.
        }
    }

    private fun vibrate() {
        try {
            if (!vibrator.hasVibrator()) return
            vibrator.vibrate(VibrationEffect.createOneShot(140, VibrationEffect.DEFAULT_AMPLITUDE))
        } catch (_: Exception) {
        }
    }
}
