package com.byd.voiceassistant

import android.Manifest
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.os.Bundle
import android.util.Log
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import com.google.android.material.chip.Chip
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Main Automotive UI & Integration Controller for BYD DiLink Voice Assistant.
 *
 * Coordinates:
 * - Chaquopy embedded Python runtime initialization (router.py)
 * - Offline Arabic Speech-to-Text via Vosk (STTEngine)
 * - Vehicle Action execution via CAN-Bus bridge (CarControlBridge)
 * - In-Cabin Spoken Response delivery via AudioFocus-managed TTS (TTSEngine)
 * - BYD Rotating Center Console adaptation (Landscape <-> Portrait configuration changes)
 */
class MainActivity : AppCompatActivity(), STTEngine.STTListener, CarControlBridge.CarActionListener {

    companion object {
        private const val TAG = "MainActivity"
        private const val REQUEST_RECORD_AUDIO_PERMISSION = 200
    }

    enum class AssistantState {
        IDLE,
        LISTENING,
        PROCESSING,
        SPEAKING
    }

    private var currentState: AssistantState = AssistantState.IDLE
    private val isProcessingUtterance = AtomicBoolean(false)

    // Core Engines
    private lateinit var carControlBridge: CarControlBridge
    private lateinit var ttsEngine: TTSEngine
    private lateinit var sttEngine: STTEngine

    // Chaquopy Python Bridge
    private var pythonRouterFn: PyObject? = null
    private var isPythonReady: Boolean = false

    // UI Elements
    private lateinit var tvUserQuery: TextView
    private lateinit var tvAssistantResponse: TextView
    private lateinit var tvIntentBadge: TextView
    private lateinit var tvCarActionStatus: TextView
    private lateinit var tvPttStatus: TextView
    private lateinit var btnPtt: ImageButton
    private lateinit var tvStatusMode: TextView
    private lateinit var tvStatusDiLink: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        initCarBridge()
        initTTS()
        initSTT()
        initChaquopyPython()
        setupListeners()
        checkAudioPermission()
    }

    private fun initViews() {
        tvUserQuery = findViewById(R.id.tv_user_query)
        tvAssistantResponse = findViewById(R.id.tv_assistant_response)
        tvIntentBadge = findViewById(R.id.tv_intent_badge)
        tvCarActionStatus = findViewById(R.id.tv_car_action_status)
        tvPttStatus = findViewById(R.id.tv_ptt_status)
        btnPtt = findViewById(R.id.btn_push_to_talk)
        tvStatusMode = findViewById(R.id.tv_status_mode)
        tvStatusDiLink = findViewById(R.id.tv_status_dilink)

        setAssistantState(AssistantState.IDLE)
    }

    private fun initCarBridge() {
        carControlBridge = CarControlBridge(this)
        carControlBridge.setCarActionListener(this)
    }

    private fun initTTS() {
        ttsEngine = TTSEngine(this) { success ->
            Log.i(TAG, "TTSEngine initialized: $success")
        }
    }

    private fun initSTT() {
        sttEngine = STTEngine(this, this)
        lifecycleScope.launch(Dispatchers.IO) {
            sttEngine.initModel(
                onReady = {
                    Log.i(TAG, "Vosk Arabic speech model loaded")
                },
                onError = { e ->
                    Log.w(TAG, "Vosk model initialization notice: ${e.message}")
                }
            )
        }
    }

    private fun initChaquopyPython() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(applicationContext))
                }
                val py = Python.getInstance()
                val routerModule = py.getModule("router")
                pythonRouterFn = routerModule["process_voice_input"]
                isPythonReady = true
                Log.i(TAG, "Chaquopy Python runtime initialized successfully")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize Chaquopy Python: ${e.message}", e)
                isPythonReady = false
            }
        }
    }

    private fun setupListeners() {
        // Push-to-Talk Button click
        btnPtt.setOnClickListener {
            handlePushToTalkClicked()
        }

        // Quick action chips for quick in-vehicle testing
        setupChipAction(R.id.chip_ac, "شغل التكييف على 22")
        setupChipAction(R.id.chip_cooler, "أبرد شوي")
        setupChipAction(R.id.chip_windows, "افتح جميع النوافذ")
        setupChipAction(R.id.chip_sunroof, "افتح فتحة السقف")
        setupChipAction(R.id.chip_volume, "ارفع الصوت")
        setupChipAction(R.id.chip_nav, "الملاحة إلى برج خليفة")
        setupChipAction(R.id.chip_weather, "كيف الطقس في الرياض؟")
        setupChipAction(R.id.chip_time, "كم الساعة الآن؟")
    }

    private fun setupChipAction(chipId: Int, promptText: String) {
        findViewById<Chip>(chipId)?.setOnClickListener {
            processUserUtterance(promptText)
        }
    }

    private fun handlePushToTalkClicked() {
        when (currentState) {
            AssistantState.IDLE -> {
                if (hasAudioPermission()) {
                    startVoiceCapture()
                } else {
                    requestAudioPermission()
                }
            }
            AssistantState.LISTENING -> {
                stopVoiceCapture()
            }
            AssistantState.SPEAKING -> {
                ttsEngine.stop()
                setAssistantState(AssistantState.IDLE)
            }
            AssistantState.PROCESSING -> {
                // Ignore while processing
            }
        }
    }

    private fun startVoiceCapture() {
        if (!sttEngine.isModelReady) {
            // Model asset might not be bundled yet; provide diagnostic advice
            Toast.makeText(this, "جاري انتظار تحميل نموذج الصوت، يمكنك الضغط على الأوامر السريعة للتجربة", Toast.LENGTH_SHORT).show()
        }

        setAssistantState(AssistantState.LISTENING)
        tvUserQuery.text = "جاري الاستماع لصوتك…"
        sttEngine.startListening()
    }

    private fun stopVoiceCapture() {
        sttEngine.stopListening()
        setAssistantState(AssistantState.PROCESSING)
    }

    /**
     * Processes transcribed or manual voice utterance through Python Router & Car Bridge.
     */
    fun processUserUtterance(rawText: String) {
        val trimmed = rawText.trim()
        if (trimmed.isEmpty()) {
            isProcessingUtterance.set(false)
            setAssistantState(AssistantState.IDLE)
            return
        }

        // Guard against duplicate / concurrent processing if onResult and onFinalResult both fire
        if (!isProcessingUtterance.compareAndSet(false, true)) {
            Log.w(TAG, "Already processing utterance, ignoring duplicate: $trimmed")
            return
        }

        // Display user query
        tvUserQuery.text = trimmed
        setAssistantState(AssistantState.PROCESSING)

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val jsonResultStr = if (isPythonReady && pythonRouterFn != null) {
                    pythonRouterFn?.call(trimmed)?.toString() ?: "{}"
                } else {
                    // Fallback JSON if Python runtime is not ready yet
                    "{\"status\":\"error\",\"intent\":\"chitchat\",\"spoken_response\":\"جاري تهيئة نظام الذكاء الاصطناعي...\",\"car_action\":null}"
                }

                val jsonResponse = JSONObject(jsonResultStr)
                val intent = jsonResponse.optString("intent", "chitchat")
                val spokenResponse = jsonResponse.optString("spoken_response", "")
                val carActionObj = jsonResponse.optJSONObject("car_action")

                var carCommand: String? = null
                var carParams: Map<String, Any> = emptyMap()

                if (carActionObj != null) {
                    carCommand = carActionObj.optString("command", "")
                    val paramsObj = carActionObj.optJSONObject("parameters")
                    val paramsMap = mutableMapOf<String, Any>()
                    if (paramsObj != null) {
                        val keys = paramsObj.keys()
                        while (keys.hasNext()) {
                            val key = keys.next()
                            paramsMap[key] = paramsObj.get(key)
                        }
                    }
                    carParams = paramsMap
                }

                // Dispatch car action on Main thread
                withContext(Dispatchers.Main) {
                    // 1. Update UI
                    updateResultUi(intent, spokenResponse, carCommand)

                    // 2. Execute vehicle control
                    if (!carCommand.isNullOrEmpty()) {
                        carControlBridge.executeAction(carCommand, carParams)
                    }

                    // 3. Spoken Audio Feedback via TTS
                    if (spokenResponse.isNotBlank()) {
                        setAssistantState(AssistantState.SPEAKING)
                        ttsEngine.speak(spokenResponse) {
                            runOnUiThread {
                                setAssistantState(AssistantState.IDLE)
                            }
                        }
                    } else {
                        setAssistantState(AssistantState.IDLE)
                    }
                }

            } catch (e: Exception) {
                Log.e(TAG, "Error in processUserUtterance pipeline: ${e.message}", e)
                withContext(Dispatchers.Main) {
                    tvAssistantResponse.text = "عذراً، حدث خطأ غير متوقع."
                    setAssistantState(AssistantState.IDLE)
                }
            }
        }
    }

    private fun updateResultUi(intent: String, spokenResponse: String, carCommand: String?) {
        tvAssistantResponse.text = spokenResponse

        // Format intent badge
        val badgeText = when (intent) {
            "car_control" -> "تحكم بالسيارة"
            "general_knowledge" -> "معلومات عامة"
            else -> "محادثة ذكية"
        }
        tvIntentBadge.text = badgeText

        if (carCommand != null) {
            tvCarActionStatus.text = "تم تنفيذ: $carCommand"
        }
    }

    private fun setAssistantState(state: AssistantState) {
        currentState = state
        if (state == AssistantState.IDLE) {
            isProcessingUtterance.set(false)
        }
        when (state) {
            AssistantState.IDLE -> {
                tvPttStatus.text = getString(R.string.ptt_idle)
                btnPtt.setColorFilter(ContextCompat.getColor(this, R.color.byd_mic_idle))
            }
            AssistantState.LISTENING -> {
                tvPttStatus.text = getString(R.string.ptt_listening)
                btnPtt.setColorFilter(ContextCompat.getColor(this, R.color.byd_mic_listening))
            }
            AssistantState.PROCESSING -> {
                tvPttStatus.text = getString(R.string.ptt_processing)
                btnPtt.setColorFilter(ContextCompat.getColor(this, R.color.byd_mic_processing))
            }
            AssistantState.SPEAKING -> {
                tvPttStatus.text = getString(R.string.ptt_speaking)
                btnPtt.setColorFilter(ContextCompat.getColor(this, R.color.byd_mic_speaking))
            }
        }
    }

    // STTEngine Callbacks
    override fun onPartialResult(partialText: String) {
        runOnUiThread {
            if (currentState == AssistantState.LISTENING) {
                tvUserQuery.text = partialText
            }
        }
    }

    override fun onFinalResult(resultText: String) {
        runOnUiThread {
            sttEngine.stopListening()
            processUserUtterance(resultText)
        }
    }

    override fun onError(exception: Exception) {
        Log.e(TAG, "STT Engine error: ${exception.message}")
        runOnUiThread {
            if (currentState == AssistantState.LISTENING) {
                setAssistantState(AssistantState.IDLE)
            }
        }
    }

    // CarControlBridge.CarActionListener Callback
    override fun onCarActionExecuted(
        command: String,
        parameters: Map<String, Any>,
        success: Boolean,
        details: String
    ) {
        runOnUiThread {
            val statusColor = if (success) R.color.byd_green_status else R.color.byd_amber_status
            tvCarActionStatus.setTextColor(ContextCompat.getColor(this, statusColor))
            tvCarActionStatus.text = details
        }
    }

    /**
     * Handles BYD DiLink screen rotation (Center Console rotates between Landscape & Portrait).
     */
    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        val isLandscape = newConfig.orientation == Configuration.ORIENTATION_LANDSCAPE
        Log.i(TAG, "DiLink Screen Rotated: isLandscape=$isLandscape")
        // No activity recreation needed; configuration handled smoothly without losing state
    }

    private fun checkAudioPermission() {
        if (!hasAudioPermission()) {
            requestAudioPermission()
        }
    }

    private fun hasAudioPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestAudioPermission() {
        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.RECORD_AUDIO),
            REQUEST_RECORD_AUDIO_PERMISSION
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_RECORD_AUDIO_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "تم تفعيل إذن الميكروفون", Toast.LENGTH_SHORT).show()
                startVoiceCapture()
            } else {
                Toast.makeText(this, "يلزم إذن الميكروفون للتعرف الصوتي", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        isProcessingUtterance.set(false)
        ttsEngine.shutdown()
        sttEngine.destroy()
    }
}
