package ru.mognu.app.data

import android.content.Context

class ProgressStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun solved(): Int = prefs.getInt(KEY, 0).coerceAtLeast(0)

    fun setSolved(value: Int) {
        prefs.edit().putInt(KEY, value.coerceAtLeast(0)).apply()
    }

    private companion object {
        const val PREFS = "mognu_progress"
        const val KEY = "solved"
    }
}
