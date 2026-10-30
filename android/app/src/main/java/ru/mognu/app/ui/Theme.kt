package ru.mognu.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val MognuBlue = Color(0xFF1565C0)
val MognuBlueDark = Color(0xFF0D47A1)
val CorrectGreen = Color(0xFF2E9B4F)

private val Colors = lightColorScheme(
    primary = MognuBlue,
    onPrimary = Color.White,
    secondary = MognuBlueDark,
    background = Color.White,
    surface = Color.White,
)

@Composable
fun MognuTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colors, content = content)
}
