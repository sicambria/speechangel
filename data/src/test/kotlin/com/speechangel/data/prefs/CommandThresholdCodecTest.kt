package com.speechangel.data.prefs

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.CommandId
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/** org.json is provided by Robolectric at test time, so this codec test runs under it. */
@RunWith(RobolectricTestRunner::class)
class CommandThresholdCodecTest {

    @Test
    fun `round-trips a threshold map`() {
        val map = mapOf(CommandId("lights") to 6.5f, CommandId("call mom") to 7.25f)
        val decoded = CommandThresholdCodec.decode(CommandThresholdCodec.encode(map))
        assertThat(decoded.keys).isEqualTo(map.keys)
        assertThat(decoded[CommandId("lights")]).isWithin(1e-4f).of(6.5f)
        assertThat(decoded[CommandId("call mom")]).isWithin(1e-4f).of(7.25f)
    }

    @Test
    fun `an empty map encodes and decodes to empty`() {
        assertThat(CommandThresholdCodec.decode(CommandThresholdCodec.encode(emptyMap()))).isEmpty()
    }

    @Test
    fun `blank or malformed input decodes to an empty map, never throws`() {
        assertThat(CommandThresholdCodec.decode("")).isEmpty()
        assertThat(CommandThresholdCodec.decode("   ")).isEmpty()
        assertThat(CommandThresholdCodec.decode("not json at all")).isEmpty()
    }
}
