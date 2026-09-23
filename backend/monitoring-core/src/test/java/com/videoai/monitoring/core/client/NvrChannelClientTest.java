package com.videoai.monitoring.core.client;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class NvrChannelClientTest {

    private static final String INPUT_PROXY_XML = """
            <?xml version="1.0" encoding="UTF-8"?>
            <InputProxyChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
              <InputProxyChannel>
                <id>1</id>
                <name>南门枪机</name>
                <sourceInputPortDescriptor>
                  <ipAddress>10.10.0.93</ipAddress>
                </sourceInputPortDescriptor>
              </InputProxyChannel>
              <InputProxyChannel>
                <id>2</id>
                <sourceInputPortDescriptor>
                  <ipAddress>10.10.0.94</ipAddress>
                </sourceInputPortDescriptor>
              </InputProxyChannel>
            </InputProxyChannelList>
            """;

    private static final String STREAMING_XML = """
            <?xml version="1.0" encoding="UTF-8"?>
            <StreamingChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
              <StreamingChannel><id>101</id><channelName>Visible Camera</channelName><enabled>true</enabled></StreamingChannel>
              <StreamingChannel><id>102</id><channelName>Visible Camera Sub</channelName><enabled>true</enabled></StreamingChannel>
              <StreamingChannel><id>201</id><channelName>Thermal Camera</channelName><enabled>true</enabled></StreamingChannel>
              <StreamingChannel><id>301</id><channelName>Disabled Camera</channelName><enabled>false</enabled></StreamingChannel>
            </StreamingChannelList>
            """;

    @Test
    void parseInputProxyChannelsReadsIdNameAndSourceIp() {
        Map<Integer, NvrChannelClient.InputProxyChannel> channels = NvrChannelClient.parseInputProxyChannels(INPUT_PROXY_XML);

        assertEquals(2, channels.size());
        assertEquals("南门枪机", channels.get(1).name());
        assertEquals("10.10.0.93", channels.get(1).ip());
        assertNull(channels.get(2).name());
        assertEquals("10.10.0.94", channels.get(2).ip());
    }

    @Test
    void parseStreamingChannelsKeepsOnlyEnabledMainStreams() {
        List<NvrChannelClient.StreamChannel> channels = NvrChannelClient.parseStreamingChannels(STREAMING_XML);

        assertEquals(2, channels.size());
        assertEquals(101, channels.get(0).id());
        assertEquals("Visible Camera", channels.get(0).channelName());
        assertEquals(201, channels.get(1).id());
    }

    @Test
    void parseStreamingChannelsTreatsMissingEnabledAsEnabled() {
        List<NvrChannelClient.StreamChannel> channels = NvrChannelClient.parseStreamingChannels(
                "<StreamingChannelList><StreamingChannel><id>101</id></StreamingChannel></StreamingChannelList>");

        assertEquals(1, channels.size());
    }

    @Test
    void parseRtspPortReadsPortNo() {
        assertEquals(8554, NvrChannelClient.parseRtspPort(
                "<NetworkPorts><RTSP><portNo>8554</portNo></RTSP></NetworkPorts>"));
        assertNull(NvrChannelClient.parseRtspPort("<NetworkPorts><HTTP><portNo>80</portNo></HTTP></NetworkPorts>"));
    }

    @Test
    void parseHandlesNonNamespacedXml() {
        Map<Integer, NvrChannelClient.InputProxyChannel> channels = NvrChannelClient.parseInputProxyChannels(
                "<InputProxyChannelList><InputProxyChannel><id>3</id>"
                        + "<sourceInputPortDescriptor><ipAddress>192.168.1.2</ipAddress></sourceInputPortDescriptor>"
                        + "</InputProxyChannel></InputProxyChannelList>");

        assertEquals(1, channels.size());
        assertEquals("192.168.1.2", channels.get(3).ip());
        assertTrue(NvrChannelClient.parseStreamingChannels(
                "<StreamingChannelList><StreamingChannel><id>302</id></StreamingChannel></StreamingChannelList>").isEmpty());
    }
}
