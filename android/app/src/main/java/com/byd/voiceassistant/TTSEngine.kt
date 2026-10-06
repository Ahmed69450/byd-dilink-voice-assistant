package com.byd.voiceassistant

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import java.util.Locale
import java.util.UUID

/**
 * High-intelligibility Automotive Text-to-Speech Engine for BYD DiLink.
 *
 * Configured specifically for Arabic vehicle prompts:
 * - Uses native Android TextToSpeech engine with Arabic locale (ar / ar-SA).
 * - Manages automotive AudioFocus (transient ducking of background music/radio).
 * - Custom tuned speech rate (1.0x) and pitch for clear in-cabin voice delivery.
 */
class TTSEngine(
    private val context: Context,
    private val onInitComplete: ((Boolean) -> Unit)? = null
) : TextToSpeech.OnInitListener {

    companion object {
        private const val TAG = "TTSEngine"
        private const val DEFAULT_SPEECH_RATE = 1.0f
        private const val DEFAULT_PITCH = 1.0f
    }

    private var tts: TextToSpeech? = null
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private var audioFocusRequest: AudioFocusRequest? = null

    var isInitialized: Boolean = false
        private set
    var isSpeaking: Boolean = false
        private set

    // Active callback map keyed by utterance ID
    private val completionCallbacks = mutableMapOf<String, () -> Unit>()

    init {
        tts = TextToSpeech(context.applicationContext, this)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val engine = tts ?: return
            var locale = Locale("ar", "SA")
            var availability = engine.isLanguageAvailable(locale)

            if (availability < TextToSpeech.LANG_AVAILABLE) {
                locale = Locale("ar")
                availability = engine.isLanguageAvailable(locale)
            }

            if (availability >= TextToSpeech.LANG_AVAILABLE) {
                engine.language = locale
                Log.i(TAG, "TTS initialized with Arabic locale: $locale")
            } else {
                Log.w(TAG, "Arabic TTS not fully available (code: $availability), fallback to default: ${Locale.getDefault()}")
                engine.language = Locale.getDefault()
            }

            engine.setSpeechRate(DEFAULT_SPEECH_RATE)
            engine.setPitch(DEFAULT_PITCH)

            setupProgressListener(engine)
            isInitialized = true
            onInitComplete?.invoke(true)
        } else {
            Log.e(TAG, "TTS initialization failed with status: $status")
            isInitialized = false
            onInitComplete?.invoke(false)
        }
    }

    private fun setupProgressListener(engine: TextToSpeech) {
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                isSpeaking = true
                Log.d(TAG, "TTS started utterance: $utteranceId")
            }

            override fun onDone(utteranceId: String?) {
                isSpeaking = false
                releaseAudioFocus()
                utteranceId?.let { id ->
                    val cb = completionCallbacks.remove(id)
                    cb?.invoke()
                }
                Log.d(TAG, "TTS completed utterance: $utteranceId")
            }

            override fun onStop(utteranceId: String?, interrupted: Boolean) {
                isSpeaking = false
                releaseAudioFocus()
                utteranceId?.let { id ->
                    val cb = completionCallbacks.remove(id)
                    cb?.invoke()
                }
                Log.d(TAG, "TTS stopped utterance: $utteranceId, interrupted: $interrupted")
            }

            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) {
                isSpeaking = false
                releaseAudioFocus()
                utteranceId?.let { id ->
                    val cb = completionCallbacks.remove(id)
                    cb?.invoke()
                }
                Log.e(TAG, "TTS error on utterance: $utteranceId")
            }

            override fun onError(utteranceId: String?, errorCode: Int) {
                isSpeaking = false
                releaseAudioFocus()
                utteranceId?.let { id ->
                    val cb = completionCallbacks.remove(id)
                    cb?.invoke()
                }
                Log.e(TAG, "TTS error $errorCode on utterance: $utteranceId")
            }
        })
    }

    /**
     * Speaks Arabic text with car media audio ducking.
     *
     * @param text Spoken response text in Arabic.
     * @param onComplete Optional callback fired when speech finishes.
     */
    fun speak(text: String, onComplete: (() -> Unit)? = null): Boolean {
        val engine = tts
        if (engine == null || !isInitialized) {
            Log.w(TAG, "Cannot speak: TTS not initialized yet")
            onComplete?.invoke()
            return false
        }

        if (text.isBlank()) {
            onComplete?.invoke()
            return true
        }

        requestAudioFocus()

        val utteranceId = "byd_tts_" + UUID.randomUUID().toString()
        if (onComplete != null) {
            completionCallbacks[utteranceId] = onComplete
        }

        val params = Bundle().apply {
            putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f)
        }

        val result = engine.speak(text, TextToSpeech.QUEUE_FLUSH, params, utteranceId)
        if (result != TextToSpeech.SUCCESS) {
            Log.e(TAG, "TTS speak failed with code: $result")
            releaseAudioFocus()
            completionCallbacks.remove(utteranceId)
            onComplete?.invoke()
            return false
        }
        return true
    }

    /**
     * Requests transient audio focus with ducking so car media lowers volume while assistant speaks.
     */
    private fun requestAudioFocus() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val playbackAttributes = AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()

                val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                    .setAudioAttributes(playbackAttributes)
                    .setAcceptsDelayedFocusGain(false)
                    .setOnAudioFocusChangeListener { focusChange ->
                        Log.d(TAG, "Audio focus changed: $focusChange")
                    }
                    .build()

                audioFocusRequest = request
                audioManager.requestAudioFocus(request)
            } else {
                @Suppress("DEPRECATION")
                audioManager.requestAudioFocus(
                    null,
                    AudioManager.STREAM_MUSIC,
                    AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
                )
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to request audio focus: ${e.message}")
        }
    }

    /**
     * Abandons audio focus so car media restores full volume.
     */
    private fun releaseAudioFocus() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                audioFocusRequest?.let { request ->
                    audioManager.abandonAudioFocusRequest(request)
                    audioFocusRequest = null
                }
            } else {
                @Suppress("DEPRECATION")
                audioManager.abandonAudioFocus(null)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to release audio focus: ${e.message}")
        }
    }

    /**
     * Stops any currently ongoing speech immediately.
     */
    fun stop() {
        try {
            tts?.stop()
            isSpeaking = false
            releaseAudioFocus()
            completionCallbacks.clear()
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping TTS: ${e.message}")
        }
    }

    /**
     * Releases TTS resources.
     */
    fun shutdown() {
        try {
            stop()
            tts?.shutdown()
            tts = null
            isInitialized = false
        } catch (e: Exception) {
            Log.e(TAG, "Error shutting down TTS: ${e.message}")
        }
    }
}
