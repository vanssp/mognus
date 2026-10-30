package ru.mognu.app

import android.app.Application
import com.yandex.mobile.ads.common.YandexAds

class MognuApp : Application() {
    override fun onCreate() {
        super.onCreate()
        YandexAds.initialize(this) { }
    }
}
