package com.byd.voiceassistant

import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import android.view.KeyEvent

/**
 * Bridge interface between Python Voice Assistant router and BYD DiLink vehicle systems.
 *
 * Implements vehicle control dispatch for:
 * - Air Conditioning / HVAC (AC_ON, AC_OFF, SET_AC_TEMP, AC_TEMP_UP, AC_TEMP_DOWN, FAN_SPEED)
 * - Windows & Sunroof (WINDOW_OPEN, WINDOW_CLOSE, WINDOW_FRONT_LEFT, WINDOW_ALL, SUNROOF_OPEN, SUNROOF_CLOSE)
 * - Media & Volume (MEDIA_PLAY, MEDIA_PAUSE, MEDIA_NEXT, MEDIA_PREV, VOLUME_UP, VOLUME_DOWN, VOLUME_SET)
 * - Navigation (NAV_TO, OPEN_MAPS)
 * - DiLink Apps & System Controls (OPEN_APP, DILINK_SETTINGS, DILINK_ENERGY_APP, DILINK_CAMERA_360)
 */
class CarControlBridge(private val context: Context) {

    companion object {
        private const val TAG = "CarControlBridge"

        // Broadcast actions for DiLink CAN-bus and System Services
        const val ACTION_BYD_CAR_CONTROL = "com.byd.carcontrol.ACTION_EXECUTE"
        const val ACTION_DILINK_HVAC = "byd.intent.action.SET_CAR_AIR"
        const val ACTION_DILINK_WINDOW = "byd.intent.action.SET_CAR_WINDOW"
        const val ACTION_DILINK_PANORAMIC = "byd.intent.action.PANORAMIC_SWITCH"

        // Standard Command Constants (matching car_commands.py)
        const val AC_ON = "AC_ON"
        const val AC_OFF = "AC_OFF"
        const val SET_AC_TEMP = "SET_AC_TEMP"
        const val AC_TEMP_UP = "AC_TEMP_UP"
        const val AC_TEMP_DOWN = "AC_TEMP_DOWN"
        const val FAN_SPEED = "FAN_SPEED"

        const val WINDOW_OPEN = "WINDOW_OPEN"
        const val WINDOW_CLOSE = "WINDOW_CLOSE"
        const val WINDOW_FRONT_LEFT = "WINDOW_FRONT_LEFT"
        const val WINDOW_ALL = "WINDOW_ALL"
        const val SUNROOF_OPEN = "SUNROOF_OPEN"
        const val SUNROOF_CLOSE = "SUNROOF_CLOSE"

        const val MEDIA_PLAY = "MEDIA_PLAY"
        const val MEDIA_PAUSE = "MEDIA_PAUSE"
        const val MEDIA_NEXT = "MEDIA_NEXT"
        const val MEDIA_PREV = "MEDIA_PREV"
        const val VOLUME_UP = "VOLUME_UP"
        const val VOLUME_DOWN = "VOLUME_DOWN"
        const val VOLUME_SET = "VOLUME_SET"

        const val NAV_TO = "NAV_TO"
        const val OPEN_MAPS = "OPEN_MAPS"

        const val OPEN_APP = "OPEN_APP"
        const val DILINK_SETTINGS = "DILINK_SETTINGS"
        const val DILINK_ENERGY_APP = "DILINK_ENERGY_APP"
        const val DILINK_CAMERA_360 = "DILINK_CAMERA_360"
    }

    interface CarActionListener {
        fun onCarActionExecuted(command: String, parameters: Map<String, Any>, success: Boolean, details: String)
    }

    private var listener: CarActionListener? = null

    fun setCarActionListener(listener: CarActionListener?) {
        this.listener = listener
    }

    // Vehicle status state tracking
    var acEnabled: Boolean = true
        private set
    var acTemperature: Double = 22.0
        private set
    var fanSpeed: Int = 3
        private set
    var sunroofOpen: Boolean = false
        private set
    var driverWindowOpen: Boolean = false
        private set
    var allWindowsOpen: Boolean = false
        private set

    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    /**
     * Executes vehicle control action.
     *
     * @param command Command constant matching car_commands.py.
     * @param parameters Parameter dictionary extracted by NLU/Python mapper.
     * @return true if action was successfully handled, false otherwise.
     */
    fun executeAction(command: String, parameters: Map<String, Any> = emptyMap()): Boolean {
        Log.i(TAG, "Executing car action: $command with params: $parameters")
        var success = false
        var details = ""

        try {
            when (command) {
                // 1. Air Conditioning / Climate Control
                AC_ON -> {
                    acEnabled = true
                    sendDiLinkBroadcast(ACTION_DILINK_HVAC, mapOf("power" to true))
                    details = "تم تشغيل التكييف"
                    success = true
                }
                AC_OFF -> {
                    acEnabled = false
                    sendDiLinkBroadcast(ACTION_DILINK_HVAC, mapOf("power" to false))
                    details = "تم إيقاف تشغيل التكييف"
                    success = true
                }
                SET_AC_TEMP -> {
                    val temp = extractDouble(parameters, "value")
                        ?: extractDouble(parameters, "temperature")
                        ?: 22.0
                    acTemperature = temp.coerceIn(16.0, 32.0)
                    acEnabled = true
                    sendDiLinkBroadcast(ACTION_DILINK_HVAC, mapOf("temp" to acTemperature, "power" to true))
                    details = "تم ضبط الحرارة على $acTemperature°C"
                    success = true
                }
                AC_TEMP_UP -> {
                    val step = extractDouble(parameters, "step") ?: 1.0
                    acTemperature = (acTemperature + step).coerceIn(16.0, 32.0)
                    acEnabled = true
                    sendDiLinkBroadcast(ACTION_DILINK_HVAC, mapOf("temp" to acTemperature, "power" to true))
                    details = "تم رفع الحرارة إلى $acTemperature°C"
                    success = true
                }
                AC_TEMP_DOWN -> {
                    val step = extractDouble(parameters, "step") ?: 1.0
                    acTemperature = (acTemperature - step).coerceIn(16.0, 32.0)
                    acEnabled = true
                    sendDiLinkBroadcast(ACTION_DILINK_HVAC, mapOf("temp" to acTemperature, "power" to true))
                    details = "تم خفض الحرارة إلى $acTemperature°C"
                    success = true
                }
                FAN_SPEED -> {
                    val speed = extractInt(parameters, "value")
                        ?: extractInt(parameters, "speed")
                        ?: 3
                    fanSpeed = speed.coerceIn(1, 7)
                    acEnabled = true
                    sendDiLinkBroadcast(ACTION_DILINK_HVAC, mapOf("fan_speed" to fanSpeed, "power" to true))
                    details = "تم ضبط سرعة المروحة على $fanSpeed"
                    success = true
                }

                // 2. Windows & Sunroof
                WINDOW_OPEN -> {
                    allWindowsOpen = true
                    sendDiLinkBroadcast(ACTION_DILINK_WINDOW, mapOf("window" to "all", "action" to "open"))
                    details = "تم فتح جميع النوافذ"
                    success = true
                }
                WINDOW_CLOSE -> {
                    allWindowsOpen = false
                    driverWindowOpen = false
                    sendDiLinkBroadcast(ACTION_DILINK_WINDOW, mapOf("window" to "all", "action" to "close"))
                    details = "تم إغلاق جميع النوافذ"
                    success = true
                }
                WINDOW_FRONT_LEFT -> {
                    val action = parameters["action"]?.toString() ?: "open"
                    driverWindowOpen = action == "open"
                    sendDiLinkBroadcast(ACTION_DILINK_WINDOW, mapOf("window" to "front_left", "action" to action))
                    details = if (driverWindowOpen) "تم فتح نافذة السائق" else "تم إغلاق نافذة السائق"
                    success = true
                }
                WINDOW_ALL -> {
                    val action = parameters["action"]?.toString() ?: "open"
                    allWindowsOpen = action == "open"
                    sendDiLinkBroadcast(ACTION_DILINK_WINDOW, mapOf("window" to "all", "action" to action))
                    details = if (allWindowsOpen) "تم فتح جميع النوافذ" else "تم إغلاق جميع النوافذ"
                    success = true
                }
                SUNROOF_OPEN -> {
                    sunroofOpen = true
                    sendDiLinkBroadcast(ACTION_BYD_CAR_CONTROL, mapOf("device" to "sunroof", "action" to "open"))
                    details = "تم فتح فتحة السقف"
                    success = true
                }
                SUNROOF_CLOSE -> {
                    sunroofOpen = false
                    sendDiLinkBroadcast(ACTION_BYD_CAR_CONTROL, mapOf("device" to "sunroof", "action" to "close"))
                    details = "تم إغلاق فتحة السقف"
                    success = true
                }

                // 3. Media & Volume
                MEDIA_PLAY -> {
                    dispatchMediaKey(KeyEvent.KEYCODE_MEDIA_PLAY)
                    details = "تم تشغيل الوسائط"
                    success = true
                }
                MEDIA_PAUSE -> {
                    dispatchMediaKey(KeyEvent.KEYCODE_MEDIA_PAUSE)
                    details = "تم إيقاف الوسائط مؤقتاً"
                    success = true
                }
                MEDIA_NEXT -> {
                    dispatchMediaKey(KeyEvent.KEYCODE_MEDIA_NEXT)
                    details = "تم الانتقال للمقطع التالي"
                    success = true
                }
                MEDIA_PREV -> {
                    dispatchMediaKey(KeyEvent.KEYCODE_MEDIA_PREVIOUS)
                    details = "تم الانتقال للمقطع السابق"
                    success = true
                }
                VOLUME_UP -> {
                    audioManager.adjustStreamVolume(
                        AudioManager.STREAM_MUSIC,
                        AudioManager.ADJUST_RAISE,
                        AudioManager.FLAG_SHOW_UI
                    )
                    details = "تم رفع مستوى الصوت"
                    success = true
                }
                VOLUME_DOWN -> {
                    audioManager.adjustStreamVolume(
                        AudioManager.STREAM_MUSIC,
                        AudioManager.ADJUST_LOWER,
                        AudioManager.FLAG_SHOW_UI
                    )
                    details = "تم خفض مستوى الصوت"
                    success = true
                }
                VOLUME_SET -> {
                    val isMute = parameters["mute"] as? Boolean ?: false
                    val value = extractInt(parameters, "value") ?: 0
                    if (isMute || value == 0) {
                        audioManager.adjustStreamVolume(
                            AudioManager.STREAM_MUSIC,
                            AudioManager.ADJUST_MUTE,
                            AudioManager.FLAG_SHOW_UI
                        )
                        details = "تم كتم الصوت"
                    } else {
                        val maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                        val targetVol = ((value.toDouble() / 30.0) * maxVol).toInt().coerceIn(0, maxVol)
                        audioManager.setStreamVolume(
                            AudioManager.STREAM_MUSIC,
                            targetVol,
                            AudioManager.FLAG_SHOW_UI
                        )
                        details = "تم ضبط مستوى الصوت على $value"
                    }
                    success = true
                }

                // 4. Navigation
                NAV_TO -> {
                    val destination = parameters["destination"]?.toString() ?: ""
                    success = launchNavigation(destination)
                    details = if (success) "جاري بدء الملاحة إلى $destination" else "تعذر فتح الملاحة"
                }
                OPEN_MAPS -> {
                    success = launchMapsApp()
                    details = if (success) "تم فتح الخرائط" else "تعذر فتح الخرائط"
                }

                // 5. Apps & DiLink System Controls
                OPEN_APP -> {
                    val appName = parameters["app_name"]?.toString() ?: ""
                    success = launchAppByName(appName)
                    details = if (success) "تم فتح تطبيق $appName" else "لم يتم العثور على تطبيق $appName"
                }
                DILINK_SETTINGS -> {
                    success = openDiLinkSettings()
                    details = "تم فتح إعدادات السيارة"
                }
                DILINK_ENERGY_APP -> {
                    success = openDiLinkEnergy()
                    details = "تم فتح إدارة الطاقة"
                }
                DILINK_CAMERA_360 -> {
                    success = openDiLinkCamera360()
                    details = "تم تشغيل كاميرا 360"
                }

                else -> {
                    // Fallback Car Control Action
                    sendDiLinkBroadcast(ACTION_BYD_CAR_CONTROL, mapOf("command" to command))
                    details = "تم تنفيذ الأمر: $command"
                    success = true
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error executing command $command", e)
            details = "خطأ في تنفيذ الأمر: ${e.message}"
            success = false
        }

        listener?.onCarActionExecuted(command, parameters, success, details)
        return success
    }

    /**
     * Emits a broadcast intent for BYD DiLink CAN-bus communication.
     */
    fun sendDiLinkBroadcast(action: String, extras: Map<String, Any> = emptyMap()) {
        try {
            val intent = Intent(action).apply {
                extras.forEach { (key, value) ->
                    when (value) {
                        is Boolean -> putExtra(key, value)
                        is Int -> putExtra(key, value)
                        is Long -> putExtra(key, value)
                        is Float -> putExtra(key, value)
                        is Double -> putExtra(key, value)
                        is String -> putExtra(key, value)
                        else -> putExtra(key, value.toString())
                    }
                }
                addFlags(Intent.FLAG_INCLUDE_STOPPED_PACKAGES)
            }
            context.sendBroadcast(intent)
            Log.d(TAG, "Broadcast sent: $action with extras $extras")
        } catch (e: Exception) {
            Log.w(TAG, "Failed to send DiLink broadcast: $action", e)
        }
    }

    private fun dispatchMediaKey(keyCode: Int) {
        try {
            val eventDown = KeyEvent(KeyEvent.ACTION_DOWN, keyCode)
            val eventUp = KeyEvent(KeyEvent.ACTION_UP, keyCode)
            audioManager.dispatchMediaKeyEvent(eventDown)
            audioManager.dispatchMediaKeyEvent(eventUp)
        } catch (e: Exception) {
            Log.e(TAG, "Error dispatching media key: $keyCode", e)
        }
    }

    private fun launchNavigation(destination: String): Boolean {
        // Try DiLink specific Navigation packages (AutoNavi Auto / Baidu Auto)
        val carNavPackages = listOf("com.autonavi.amapauto", "com.baidu.BaiduMap.auto")
        for (pkg in carNavPackages) {
            val launchIntent = context.packageManager.getLaunchIntentForPackage(pkg)
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(launchIntent)
                return true
            }
        }

        // Standard Android Geo URI Intent
        return try {
            val uri = Uri.parse("geo:0,0?q=" + Uri.encode(destination))
            val mapIntent = Intent(Intent.ACTION_VIEW, uri).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(mapIntent)
            true
        } catch (e: Exception) {
            Log.w(TAG, "Generic geo intent navigation failed: ${e.message}")
            false
        }
    }

    private fun launchMapsApp(): Boolean {
        val carNavPackages = listOf("com.autonavi.amapauto", "com.baidu.BaiduMap.auto", "com.google.android.apps.maps")
        for (pkg in carNavPackages) {
            val launchIntent = context.packageManager.getLaunchIntentForPackage(pkg)
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(launchIntent)
                return true
            }
        }

        return try {
            val mapIntent = Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0")).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(mapIntent)
            true
        } catch (e: Exception) {
            Log.w(TAG, "Failed to launch maps app: ${e.message}")
            false
        }
    }

    private fun launchAppByName(appName: String): Boolean {
        val pm = context.packageManager
        val cleanName = appName.trim().lowercase()

        // Known mapping of common app names to package names
        val commonApps = mapOf(
            "سبوتيفاي" to "com.spotify.music",
            "spotify" to "com.spotify.music",
            "يوتيوب" to "com.google.android.youtube",
            "youtube" to "com.google.android.youtube",
            "خرائط" to "com.google.android.apps.maps",
            "الخرائط" to "com.google.android.apps.maps",
            "انغامي" to "com.anghami",
            "anghami" to "com.anghami",
            "راديو" to "com.byd.radio"
        )

        val targetPkg = commonApps[cleanName]
        if (targetPkg != null) {
            val intent = pm.getLaunchIntentForPackage(targetPkg)
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                return true
            }
        }

        // Search installed apps by label
        try {
            val packages = pm.getInstalledApplications(0)
            for (appInfo in packages) {
                val label = pm.getApplicationLabel(appInfo).toString().lowercase()
                if (label.contains(cleanName) || cleanName.contains(label)) {
                    val intent = pm.getLaunchIntentForPackage(appInfo.packageName)
                    if (intent != null) {
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        context.startActivity(intent)
                        return true
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error searching applications for $appName", e)
        }

        return false
    }

    private fun openDiLinkSettings(): Boolean {
        return try {
            val intent = context.packageManager.getLaunchIntentForPackage("com.byd.set")
                ?: context.packageManager.getLaunchIntentForPackage("com.byd.settings")
                ?: Intent(Settings.ACTION_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to open settings", e)
            false
        }
    }

    private fun openDiLinkEnergy(): Boolean {
        return try {
            val intent = context.packageManager.getLaunchIntentForPackage("com.byd.energy")
                ?: context.packageManager.getLaunchIntentForPackage("com.byd.evmanager")
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                true
            } else {
                sendDiLinkBroadcast("com.byd.action.OPEN_ENERGY_MANAGEMENT")
                true
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to open energy app", e)
            false
        }
    }

    private fun openDiLinkCamera360(): Boolean {
        return try {
            val intent = context.packageManager.getLaunchIntentForPackage("com.byd.panoramic")
                ?: context.packageManager.getLaunchIntentForPackage("com.byd.camera360")
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                true
            } else {
                sendDiLinkBroadcast(ACTION_DILINK_PANORAMIC, mapOf("state" to "on"))
                true
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to open 360 camera", e)
            false
        }
    }

    private fun extractDouble(map: Map<String, Any>, key: String): Double? {
        val v = map[key] ?: return null
        return when (v) {
            is Number -> v.toDouble()
            is String -> v.toDoubleOrNull()
            else -> null
        }
    }

    private fun extractInt(map: Map<String, Any>, key: String): Int? {
        val v = map[key] ?: return null
        return when (v) {
            is Number -> v.toInt()
            is String -> v.toIntOrNull()
            else -> null
        }
    }
}
