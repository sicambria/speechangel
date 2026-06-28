package com.speechangel.data

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.FeatureSequence
import org.junit.Test

class FeatureCodecTest {

    @Test
    fun `encode then decode round-trips a feature sequence`() {
        val original = FeatureSequence(
            listOf(
                floatArrayOf(1.5f, -2.25f, 0f),
                floatArrayOf(3.125f, 4f, -5.5f),
            ),
        )
        val decoded = FeatureCodec.decode(FeatureCodec.encode(original))
        assertThat(decoded.frameCount).isEqualTo(2)
        assertThat(decoded.coefficientCount).isEqualTo(3)
        assertThat(decoded.frames[0]).usingExactEquality().containsExactly(1.5f, -2.25f, 0f)
        assertThat(decoded.frames[1]).usingExactEquality().containsExactly(3.125f, 4f, -5.5f)
    }

    @Test
    fun `decoding an empty blob yields an empty sequence`() {
        assertThat(FeatureCodec.decode(ByteArray(0)).isEmpty).isTrue()
    }
}
