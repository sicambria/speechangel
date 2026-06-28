package com.speechangel.app.service

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class OemAutostartTest {

    @Test
    fun `a known manufacturer yields steps and a settings deep-link`() {
        val g = OemAutostart.resolve("Xiaomi")
        assertThat(g.steps).isNotEmpty()
        assertThat(g.hasDeepLink).isTrue()
        assertThat(g.autostartPackage).isEqualTo("com.miui.securitycenter")
    }

    @Test
    fun `matching is case-insensitive and matches sub-brands`() {
        assertThat(OemAutostart.resolve("REDMI Note 12").autostartPackage).isEqualTo("com.miui.securitycenter")
        assertThat(OemAutostart.resolve("realme GT").autostartPackage).isEqualTo("com.coloros.safecenter")
    }

    @Test
    fun `samsung has steps but no deep-link component`() {
        val g = OemAutostart.resolve("samsung")
        assertThat(g.steps).isNotEmpty()
        assertThat(g.hasDeepLink).isFalse()
    }

    @Test
    fun `an unknown manufacturer falls back to generic guidance`() {
        val g = OemAutostart.resolve("Google")
        assertThat(g.steps).isNotEmpty()
        assertThat(g.hasDeepLink).isFalse()
    }
}
