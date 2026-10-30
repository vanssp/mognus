package ru.mognu.app.ads

import android.app.Activity
import android.os.Handler
import android.os.Looper
import com.yandex.mobile.ads.common.AdError
import com.yandex.mobile.ads.common.AdRequest
import com.yandex.mobile.ads.common.AdRequestError
import com.yandex.mobile.ads.common.ImpressionData
import com.yandex.mobile.ads.interstitial.InterstitialAd
import com.yandex.mobile.ads.interstitial.InterstitialAdEventListener
import com.yandex.mobile.ads.interstitial.InterstitialAdLoadListener
import com.yandex.mobile.ads.interstitial.InterstitialAdLoader

/**
 * Production interstitial. If the ad fails to load or the player closes it,
 * [showThen] still continues the game.
 */
class YandexInterstitial(
    private val activity: Activity,
) {
    private val handler = Handler(Looper.getMainLooper())
    private val loader = InterstitialAdLoader(activity)
    private var ad: InterstitialAd? = null
    private var loading = false
    private var failed = false
    private var pending: (() -> Unit)? = null
    private var timeout: Runnable? = null

    fun preload() {
        if (loading || ad != null) return
        loading = true
        failed = false
        val request = AdRequest.Builder(AD_UNIT_ID).build()
        loader.loadAd(
            request,
            object : InterstitialAdLoadListener {
                override fun onAdLoaded(interstitialAd: InterstitialAd) {
                    loading = false
                    ad = interstitialAd
                    val waiting = pending
                    if (waiting != null) {
                        pending = null
                        cancelTimeout()
                        showNow(waiting)
                    }
                }

                override fun onAdFailedToLoad(error: AdRequestError) {
                    loading = false
                    failed = true
                    ad = null
                    val waiting = pending
                    if (waiting != null) {
                        pending = null
                        cancelTimeout()
                        waiting()
                    }
                }
            },
        )
    }

    fun showThen(onFinished: () -> Unit) {
        val ready = ad
        if (ready != null) {
            showNow(onFinished)
            return
        }
        if (!loading || failed) {
            onFinished()
            preload()
            return
        }
        pending = onFinished
        val wait = Runnable {
            val waiting = pending ?: return@Runnable
            pending = null
            if (ad != null) {
                showNow(waiting)
            } else {
                waiting()
            }
        }
        timeout = wait
        handler.postDelayed(wait, LOAD_WAIT_MS)
    }

    fun destroy() {
        cancelTimeout()
        pending = null
        ad?.setAdEventListener(null)
        ad = null
    }

    private fun showNow(onFinished: () -> Unit) {
        val ready = ad
        if (ready == null) {
            onFinished()
            preload()
            return
        }
        var finished = false
        val done = {
            if (!finished) {
                finished = true
                ready.setAdEventListener(null)
                if (ad === ready) ad = null
                onFinished()
                preload()
            }
        }
        ready.setAdEventListener(
            object : InterstitialAdEventListener {
                override fun onAdShown() = Unit

                override fun onAdFailedToShow(adError: AdError) = done()

                override fun onAdDismissed() = done()

                override fun onAdClicked() = Unit

                override fun onAdImpression(impressionData: ImpressionData?) = Unit
            },
        )
        try {
            ready.show(activity)
        } catch (_: Exception) {
            done()
        }
    }

    private fun cancelTimeout() {
        timeout?.let { handler.removeCallbacks(it) }
        timeout = null
    }

    private companion object {
        const val AD_UNIT_ID = "R-M-20308351-1"
        const val LOAD_WAIT_MS = 4_000L
    }
}
