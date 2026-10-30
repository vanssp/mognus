# могну

Игра «кто кого могнет»: на экране две фотографии, нужно нажать на того, кто сильнее. 200 пар подряд — звери, птицы, рыбы, насекомые и микробы. Верный ответ сразу открывает следующую пару. Ошибка коротко вибрирует, звучит и объясняет, почему сильнее другой; дальше можно идти только после этого объяснения. Прогресс сохраняется. После каждой 10-й, 20-й, … 200-й пары показывается межстраничная реклама Яндекса, затем игра продолжается. Когда все пары решены, открывается финальный экран.

Рекламный блок: `R-M-20308351-1`.

Картинки — сжатый WebP (длинная сторона около 720 px), источники и лицензии в [`CREDITS.md`](CREDITS.md). Пара «эпулописциум / лактобацилла» заменена на «китоглав / африканская якана»: у гигантской бактерии эпулописциум не нашлось свободной фотографии.

## Android Studio

1. Установите Android Studio и Android SDK (compileSdk 36).
2. Откройте папку `android/` как проект.
3. Дождитесь синхронизации Gradle и запустите конфигурацию `app`.

## Debug APK из командной строки

Нужны JDK 17 и Android SDK. Укажите путь к SDK в `android/local.properties` (`sdk.dir=...`) или в переменной `ANDROID_HOME`.

```bash
cd android
./gradlew :app:assembleDebug
```

Готовый файл: `android/app/build/outputs/apk/debug/app-debug.apk`.

## English

**могну** is a native Android game (Kotlin, Jetpack Compose, minSdk 26). The player looks at two creature photos and taps the stronger one. There are 200 fixed pairs. A correct tap plays a short chime and moves on. A wrong tap vibrates, plays a dull buzz, and shows a short Russian explanation; the round does not advance until the player has seen who was right. Progress is stored on the device. A Yandex Mobile Ads interstitial (`R-M-20308351-1`) is shown after questions 10, 20, … 200. Photos are compressed WebP files; see `CREDITS.md` for the source page and license of each image.

Open the `android/` directory in Android Studio, or build a debug APK with `./gradlew :app:assembleDebug`.
