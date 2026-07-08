package com.speechangel.core.enrollment

import com.speechangel.core.dsp.Vad
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.Template

/**
 * Pure, deterministic streaming state machine for the two-stage (wake → command) listen loop.
 *
 * It owns the sliding wake/command buffers and the `wakeDetected` latch; [onFrame] consumes one
 * fixed-size audio frame and returns what the host should do next. There is no Android, no
 * dispatcher, and no I/O here — two things follow from that:
 *
 *  1. The wake→command transition is unit-testable without a device (it was previously inlined in
 *     `ListeningService` and had zero tests).
 *  2. The heavy MFCC/DTW work [onFrame] triggers is confined to a single synchronous call, so the
 *     host can run the whole thing on a background dispatcher — keeping it off the main thread.
 *
 * Caller contract: only call [onFrame] with a non-empty [Template] set (handle "no templates" — the
 * idle path — before calling), and call [reset] whenever listening pauses so stale audio is dropped.
 */
class WakeGatedRecognizer(
    private val recognizer: Recognizer,
    private val wakeWordGate: WakeWordGate,
    private val vad: Vad,
    sampleRateHz: Int,
    windowMs: Int = DEFAULT_WINDOW_MS,
    wakeWindowMs: Int = DEFAULT_WAKE_WINDOW_MS,
    /** E04-06: Number of consecutive wake-positive frames required before Stage-2 triggers. */
    private val wakePersistence: Int = 1,
) {
    /** What the host should do after feeding a frame. */
    sealed interface Outcome {
        /** Still buffering — wake-gating, or accumulating a command window. Keep feeding frames. */
        data object Pending : Outcome

        /** The wake word just fired; the command window is now being accumulated from the next frame. */
        data object Woke : Outcome

        /** A full command window completed and was evaluated. [result] is the recogniser verdict. */
        data class Recognized(val result: RecognitionResult) : Outcome
    }

    private val targetSamples = sampleRateHz * windowMs / 1000
    private val wakeWindowSamples = sampleRateHz * wakeWindowMs / 1000
    private val cmdBuf = ArrayDeque<AudioSamples>()
    private val wakeBuf = ArrayDeque<AudioSamples>()
    private var wakeDetected = false
    /** E04-06: Count of consecutive wake-positive frames. Reset on NoWake. */
    private var consecutiveWakes = 0

    /** Clears all buffered audio and the wake latch. Call when listening pauses or templates clear. */
    fun reset() {
        cmdBuf.clear()
        wakeBuf.clear()
        wakeDetected = false
        consecutiveWakes = 0
    }

    /**
     * Feed one frame plus the current template set ([all] still includes reserved/wake templates;
     * the split is done here). Returns [Outcome.Recognized] only on the frame that completes a
     * command window. When a wake word is enrolled, Stage-2 is gated until [Outcome.Woke].
     */
    fun onFrame(frame: AudioSamples, all: List<Template>, thresholds: Map<CommandId, Float> = emptyMap()): Outcome {
        val wakeTemplates = all.filter { it.commandId == ReservedCommands.WAKE }
        val cmdTemplates = ReservedCommands.commandTemplates(all)

        if (wakeTemplates.isNotEmpty() && !wakeDetected) {
            wakeBuf.add(frame)
            while (wakeBuf.sumOf { it.samples.size } > wakeWindowSamples) wakeBuf.removeFirst()
            val wakeWindow = vad.trim(AudioSamples.concat(wakeBuf))
            return when (wakeWordGate.evaluate(wakeWindow, wakeTemplates)) {
                is WakeDecision.Wake -> {
                    consecutiveWakes++
                    if (consecutiveWakes >= wakePersistence) {
                        wakeDetected = true
                        wakeBuf.clear()
                        cmdBuf.clear()
                        consecutiveWakes = 0
                        Outcome.Woke
                    } else {
                        Outcome.Pending
                    }
                }
                is WakeDecision.NoWake -> {
                    consecutiveWakes = 0
                    Outcome.Pending
                }
            }
        }

        cmdBuf.add(frame)
        if (cmdBuf.sumOf { it.samples.size } < targetSamples) return Outcome.Pending

        val window = AudioSamples.concat(cmdBuf)
        cmdBuf.clear()
        wakeBuf.clear()
        wakeDetected = false
        return Outcome.Recognized(recognizer.recognize(window, cmdTemplates, thresholds))
    }

    companion object {
        const val DEFAULT_WINDOW_MS = 1_500
        const val DEFAULT_WAKE_WINDOW_MS = 750
    }
}
