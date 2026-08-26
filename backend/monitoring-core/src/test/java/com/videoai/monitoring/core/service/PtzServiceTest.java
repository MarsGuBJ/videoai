package com.videoai.monitoring.core.service;

import com.videoai.monitoring.core.service.PtzService.PtzPlan;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class PtzServiceTest {

    @Test
    void ptzVectorScalesAndClampsStep() {
        assertArrayEquals(new int[]{0, 50, 0}, PtzService.ptzVector("up", 5));
        assertArrayEquals(new int[]{0, -50, 0}, PtzService.ptzVector("down", 5));
        assertArrayEquals(new int[]{-50, 0, 0}, PtzService.ptzVector("left", 5));
        assertArrayEquals(new int[]{50, 0, 0}, PtzService.ptzVector("right", 5));
        assertArrayEquals(new int[]{-50, 50, 0}, PtzService.ptzVector("up_left", 5));
        assertArrayEquals(new int[]{50, 50, 0}, PtzService.ptzVector("up_right", 5));
        assertArrayEquals(new int[]{-50, -50, 0}, PtzService.ptzVector("down_left", 5));
        assertArrayEquals(new int[]{50, -50, 0}, PtzService.ptzVector("down_right", 5));
        assertArrayEquals(new int[]{0, 0, 50}, PtzService.ptzVector("zoom_in", 5));
        assertArrayEquals(new int[]{0, 0, -50}, PtzService.ptzVector("zoom_out", 5));
        assertArrayEquals(new int[]{0, 0, 0}, PtzService.ptzVector("stop", 5));
        // clamped to [1, 10] * 10
        assertArrayEquals(new int[]{0, 10, 0}, PtzService.ptzVector("up", 0));
        assertArrayEquals(new int[]{0, 100, 0}, PtzService.ptzVector("up", 99));
        assertArrayEquals(new int[]{0, 10, 0}, PtzService.ptzVector("up", null));
    }

    @Test
    void planBuildsContinuousMoveXml() {
        PtzPlan plan = PtzService.plan("UP", 5, null, "1");
        assertEquals("PUT", plan.method());
        assertEquals("/ISAPI/PTZCtrl/channels/1/continuous", plan.path());
        assertEquals("<PTZData><pan>0</pan><tilt>50</tilt><zoom>0</zoom></PTZData>", plan.body());
    }

    @Test
    void planBuildsHomeAndPresetGoto() {
        PtzPlan home = PtzService.plan("home", null, null, "3");
        assertEquals("/ISAPI/PTZCtrl/channels/3/homeposition/goto", home.path());
        assertEquals("", home.body());

        PtzPlan preset = PtzService.plan("preset_goto", null, 7, "3");
        assertEquals("/ISAPI/PTZCtrl/channels/3/presets/7/goto", preset.path());
        assertEquals("", preset.body());
    }

    @Test
    void planRejectsInvalidPresetAndUnknownCommand() {
        assertThrows(ResponseStatusException.class, () -> PtzService.plan("preset_goto", null, 0, "1"));
        assertThrows(ResponseStatusException.class, () -> PtzService.plan("preset_goto", null, 256, "1"));
        assertThrows(ResponseStatusException.class, () -> PtzService.plan("preset_goto", null, null, "1"));
        assertThrows(ResponseStatusException.class, () -> PtzService.plan("spin", 5, null, "1"));
    }

    @Test
    void parsesTrackIdFromRtspPath() {
        assertEquals("101", PtzService.parseTrackId("/Streaming/Channels/101"));
        assertEquals("1601", PtzService.parseTrackId("/Streaming/Channels/1601/picture"));
        assertNull(PtzService.parseTrackId("/stream01"));
        assertNull(PtzService.parseTrackId(null));
    }

    @Test
    void normalizesHikvisionChannel() {
        assertEquals("1", PtzService.normalizeChannel("101"));
        assertEquals("16", PtzService.normalizeChannel("1602"));
        assertEquals("5", PtzService.normalizeChannel("5"));
        assertEquals("12", PtzService.normalizeChannel("12"));
        assertNull(PtzService.normalizeChannel(null));
        assertNull(PtzService.normalizeChannel("  "));
    }
}
