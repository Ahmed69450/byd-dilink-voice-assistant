package com.byd.voiceassistant

import android.content.Context
import android.util.Log
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import org.vosk.android.StorageService
import java.io.File
import java.io.IOException

/**
 * Offline Arabic Speech-to-Text Engine powered by Vosk SDK.
 *
 * Runs completely on-device without internet access:
 * - Unpacks and streams microphone PCM audio into VoskRecognizer.
 * - Extracts partial and final transcribed Arabic hypotheses.
 * - Dispatches callbacks to the UI and Intent Router.
 */
class STTEngine(
    private val context: Context,
    private val listener: STTListener? = null
) : RecognitionListener {

    companion object {
        private const val TAG = "STTEngine"
        private const val SAMPLE_RATE = 16000.0f
        private const val MODEL_DIR = "model-ar"
    }

    interface STTListener {
        fun onReady() {}
        fun onPartialResult(partialText: String) {}
        fun onResult(resultText: String) {}
        fun onFinalResult(resultText: String) {}
        fun onError(exception: Exception) {}
    }

    private var model: Model? = null
    private var speechService: SpeechService? = null
    private var recognizer: Recognizer? = null
    private var hasDispatchedFinalResult: Boolean = false
    var isListening: Boolean = false
        private set
    var isModelReady: Boolean = false
        private set

    /**
     * Initializes the Vosk Arabic language model from assets or local storage.
     */
    fun initModel(
        onReady: () -> Unit = {},
        onError: (Exception) -> Unit = {}
    ) {
        // First check if already extracted in app external/files dir
        val externalModelDir = File(context.getExternalFilesDir(null), MODEL_DIR)
        if (externalModelDir.exists() && externalModelDir.isDirectory) {
            try {
                model = Model(externalModelDir.absolutePath)
                isModelReady = true
                Log.i(TAG, "Vosk model loaded from storage: ${externalModelDir.absolutePath}")
                listener?.onReady()
                onReady()
                return
            } catch (e: Exception) {
                Log.w(TAG, "Failed loading from storage, attempting asset unpack: ${e.message}")
            }
        }

        // Unpack from assets
        StorageService.unpack(
            context,
            MODEL_DIR,
            "model",
            { loadedModel: Model ->
                this.model = loadedModel
                isModelReady = true
                Log.i(TAG, "Vosk model unpacked and initialized successfully from assets")
                listener?.onReady()
                onReady()
            },
            { exception: IOException ->
                Log.e(TAG, "Failed to unpack Vosk model from assets: ${exception.message}")
                isModelReady = false
                listener?.onError(exception)
                onError(exception)
            }
        )
    }

    /**
     * Starts audio recording and real-time streaming recognition.
     */
    fun startListening(): Boolean {
        val currentModel = model
        if (currentModel == null || !isModelReady) {
            val err = IllegalStateException("Vosk speech model is not ready. Call initModel() first.")
            Log.e(TAG, err.message ?: "")
            listener?.onError(err)
            return false
        }

        if (isListening) {
            return true
        }

        return try {
            // Clean up previous service and recognizer instances to avoid native resource leaks
            speechService?.stop()
            speechService?.shutdown()
            speechService = null
            recognizer?.close()
            recognizer = null

            val rec = Recognizer(currentModel, SAMPLE_RATE)
            recognizer = rec
            val service = SpeechService(rec, SAMPLE_RATE)
            speechService = service
            hasDispatchedFinalResult = false

            service.startListening(this)
            isListening = true
            Log.i(TAG, "STT listening started at $SAMPLE_RATE Hz")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start speech service: ${e.message}", e)
            listener?.onError(e)
            isListening = false
            false
        }
    }

    /**
     * Stops listening and completes recognition.
     */
    fun stopListening() {
        if (!isListening) return

        try {
            speechService?.stop()
            isListening = false
            Log.i(TAG, "STT listening stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping speech service: ${e.message}", e)
        }
    }

    /**
     * Destroys and cleans up recognizer resources.
     */
    fun destroy() {
        try {
            isListening = false
            speechService?.stop()
            speechService?.shutdown()
            speechService = null
            recognizer?.close()
            recognizer = null
            model = null
            isModelReady = false
        } catch (e: Exception) {
            Log.e(TAG, "Error destroying STTEngine: ${e.message}", e)
        }
    }

    override fun onPartialResult(hypothesis: String?) {
        if (hypothesis.isNullOrBlank()) return
        val text = parseVoskJson(hypothesis, "partial")
        if (text.isNotBlank()) {
            listener?.onPartialResult(text)
        }
    }

    override fun onResult(hypothesis: String?) {
        if (hypothesis.isNullOrBlank()) return
        val text = parseVoskJson(hypothesis, "text")
        if (text.isNotBlank()) {
            listener?.onResult(text)
            if (!hasDispatchedFinalResult) {
                hasDispatchedFinalResult = true
                listener?.onFinalResult(text)
            }
        }
    }

    override fun onFinalResult(hypothesis: String?) {
        if (hypothesis.isNullOrBlank()) return
        val text = parseVoskJson(hypothesis, "text")
        if (text.isNotBlank() && !hasDispatchedFinalResult) {
            hasDispatchedFinalResult = true
            listener?.onFinalResult(text)
        }
    }

    override fun onError(exception: Exception?) {
        Log.e(TAG, "Vosk recognition error: ${exception?.message}", exception)
        exception?.let { listener?.onError(it) }
    }

    override fun onTimeout() {
        Log.w(TAG, "Vosk recognition timeout")
        stopListening()
    }

    private fun parseVoskJson(jsonStr: String, key: String): String {
        return try {
            val json = JSONObject(jsonStr)
            json.optString(key, "").trim()
        } catch (e: Exception) {
            ""
        }
    }
}
