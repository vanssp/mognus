package ru.mognu.app.ui

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import ru.mognu.app.R
import ru.mognu.app.data.Question

enum class Screen { Launch, Play, End }

@Composable
fun LaunchScreen(solved: Int, total: Int, onStart: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Logo(Modifier.size(220.dp))
        Spacer(Modifier.height(20.dp))
        Text(
            text = stringResource(R.string.app_name),
            color = MognuBlueDark,
            fontSize = 56.sp,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = stringResource(R.string.subtitle),
            color = MognuBlue,
            fontSize = 20.sp,
        )
        if (solved in 1 until total) {
            Spacer(Modifier.height(12.dp))
            Text(
                text = stringResource(R.string.progress_done, solved, total),
                color = Color(0xFF5C6B7A),
                fontSize = 16.sp,
            )
        }
        Spacer(Modifier.height(28.dp))
        Button(
            onClick = onStart,
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MognuBlue),
        ) {
            Text(stringResource(R.string.start), fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
fun PlayScreen(
    question: Question,
    solved: Int,
    total: Int,
    revealed: Boolean,
    onPick: (String) -> Unit,
    onNext: () -> Unit,
) {
    Box(Modifier.fillMaxSize().background(Color.Black)) {
        Column(Modifier.fillMaxSize()) {
            CreatureHalf(
                name = question.nameA,
                file = question.imageA,
                nameAtBottom = true,
                highlighted = revealed && question.winner == "a",
                modifier = Modifier.weight(1f),
                onClick = { onPick("a") },
            )
            ProgressBar(solved = solved, total = total)
            CreatureHalf(
                name = question.nameB,
                file = question.imageB,
                nameAtBottom = false,
                highlighted = revealed && question.winner == "b",
                modifier = Modifier.weight(1f),
                onClick = { onPick("b") },
            )
        }
        if (revealed) {
            ExplanationCard(
                text = question.explanation,
                onNext = onNext,
                modifier = Modifier
                    .align(Alignment.Center)
                    .padding(horizontal = 20.dp),
            )
        }
    }
}

@Composable
fun EndScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Logo(Modifier.size(180.dp))
        Spacer(Modifier.height(24.dp))
        Text(
            text = stringResource(R.string.end_title),
            color = MognuBlueDark,
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.end_body),
            color = Color(0xFF37474F),
            fontSize = 20.sp,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun Logo(modifier: Modifier) {
    val context = LocalContext.current
    val bitmap = produceState<ImageBitmap?>(null) {
        value = withContext(Dispatchers.IO) {
            context.assets.open("logo.webp").use { stream ->
                BitmapFactory.decodeStream(stream)?.asImageBitmap()
            }
        }
    }.value
    if (bitmap != null) {
        Image(
            bitmap = bitmap,
            contentDescription = stringResource(R.string.logo_description),
            modifier = modifier,
            contentScale = ContentScale.Fit,
        )
    } else {
        Spacer(modifier)
    }
}

@Composable
private fun CreatureHalf(
    name: String,
    file: String,
    nameAtBottom: Boolean,
    highlighted: Boolean,
    modifier: Modifier,
    onClick: () -> Unit,
) {
    val bitmap = rememberAssetBitmap("images/$file")
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        if (bitmap != null) {
            Image(
                bitmap = bitmap,
                contentDescription = stringResource(R.string.creature_description, name),
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
        } else {
            Box(Modifier.fillMaxSize().background(Color(0xFF263238)))
        }
        if (highlighted) {
            Box(Modifier.fillMaxSize().border(8.dp, CorrectGreen))
        }
        val gradient = if (nameAtBottom) {
            Brush.verticalGradient(listOf(Color.Transparent, Color(0xCC000000)))
        } else {
            Brush.verticalGradient(listOf(Color(0xCC000000), Color.Transparent))
        }
        Box(
            modifier = Modifier
                .align(if (nameAtBottom) Alignment.BottomCenter else Alignment.TopCenter)
                .fillMaxWidth()
                .height(72.dp)
                .background(gradient),
            contentAlignment = if (nameAtBottom) Alignment.BottomCenter else Alignment.TopCenter,
        ) {
            Text(
                text = name,
                color = Color.White,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .padding(horizontal = 16.dp, vertical = 10.dp)
                    .then(if (nameAtBottom) Modifier.padding(bottom = 2.dp) else Modifier),
            )
        }
    }
}

@Composable
private fun ProgressBar(solved: Int, total: Int) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(36.dp)
            .background(Color.Black),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(4.dp)
                .background(MognuBlue),
        )
        Text(
            text = stringResource(R.string.progress, solved.coerceAtMost(total), total),
            color = MognuBlueDark,
            fontWeight = FontWeight.Bold,
            fontSize = 14.sp,
            modifier = Modifier
                .clip(RoundedCornerShape(20.dp))
                .background(Color.White)
                .padding(horizontal = 12.dp, vertical = 4.dp),
        )
    }
}

@Composable
private fun ExplanationCard(text: String, onNext: () -> Unit, modifier: Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(18.dp))
            .background(Color.White)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = {},
            )
            .padding(18.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = text,
            color = Color(0xFF1A237E),
            fontSize = 18.sp,
            textAlign = TextAlign.Center,
            lineHeight = 24.sp,
        )
        Spacer(Modifier.height(14.dp))
        Button(
            onClick = onNext,
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MognuBlue),
        ) {
            Text(stringResource(R.string.next), fontSize = 18.sp)
        }
    }
}

@Composable
private fun rememberAssetBitmap(path: String): ImageBitmap? {
    val context = LocalContext.current
    return produceState<ImageBitmap?>(initialValue = null, path) {
        value = withContext(Dispatchers.IO) {
            runCatching {
                context.assets.open(path).use { stream ->
                    BitmapFactory.decodeStream(stream)?.asImageBitmap()
                }
            }.getOrNull()
        }
    }.value
}
