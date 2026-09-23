package com.videoai.monitoring.core.client;

import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

import java.net.http.HttpResponse;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

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

    // ---- fetchDevice：CVR（无 Streaming/channels）回退到 InputProxy ----

    /** 现场 CVR（DS-A80348S）InputProxy 通道：通道号即 id，主码流 trackId = id * 100 + 1。 */
    private static final String CVR_INPUT_PROXY_XML = """
            <?xml version="1.0" encoding="UTF-8"?>
            <InputProxyChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
              <InputProxyChannel>
                <id>12</id>
                <name>B6-1F-室外B5侧2</name>
                <sourceInputPortDescriptor><ipAddress>172.21.111.12</ipAddress></sourceInputPortDescriptor>
              </InputProxyChannel>
              <InputProxyChannel>
                <id>108</id>
                <name>B1-1F-4#楼梯间出入口2</name>
                <sourceInputPortDescriptor><ipAddress>172.21.111.11</ipAddress></sourceInputPortDescriptor>
              </InputProxyChannel>
            </InputProxyChannelList>
            """;

    private static HttpResponse<String> response(int status, String body) {
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(status);
        when(response.body()).thenReturn(body);
        return response;
    }

    private static IsapiDigestClient stubClient(int inputProxyStatus, String inputProxyBody,
                                               int streamingStatus, String streamingBody) throws Exception {
        // 先构造好各响应，再统一 stub：Mockito 不允许在 when(...) 内部再对另一个 mock 打桩
        HttpResponse<String> deviceInfo = response(200, "<DeviceInfo/>");
        HttpResponse<String> inputProxy = response(inputProxyStatus, inputProxyBody);
        HttpResponse<String> streaming = response(streamingStatus, streamingBody);
        HttpResponse<String> ports = response(200, "<NetworkPorts><RTSP><portNo>554</portNo></RTSP></NetworkPorts>");

        IsapiDigestClient client = mock(IsapiDigestClient.class);
        when(client.get(contains("/ISAPI/System/deviceInfo"), anyString(), anyString()))
                .thenReturn(deviceInfo);
        when(client.get(contains("/ISAPI/ContentMgmt/InputProxy/channels"), anyString(), anyString()))
                .thenReturn(inputProxy);
        when(client.get(contains("/ISAPI/Streaming/channels"), anyString(), anyString()))
                .thenReturn(streaming);
        when(client.get(contains("/ISAPI/System/Network/ports"), anyString(), anyString()))
                .thenReturn(ports);
        return client;
    }

    @Test
    void fetchDeviceFallsBackToInputProxyWhenStreamingForbidden() throws Exception {
        NvrChannelClient nvr = new NvrChannelClient(stubClient(200, CVR_INPUT_PROXY_XML, 403, "forbidden"));

        NvrChannelClient.NvrDevice device = nvr.fetchDevice("172.21.200.21", 80, "admin", "pw");

        assertEquals(2, device.channels().size());
        // 按通道号升序：12 → trackId 1201，108 → trackId 10801（现场实测 108 → 10801）
        assertEquals(12, device.channels().get(0).channel());
        assertEquals(1201, device.channels().get(0).trackId());
        assertEquals("B6-1F-室外B5侧2", device.channels().get(0).name());
        assertEquals("172.21.111.12", device.channels().get(0).sourceIp());
        assertEquals(108, device.channels().get(1).channel());
        assertEquals(10801, device.channels().get(1).trackId());
        assertEquals("B1-1F-4#楼梯间出入口2", device.channels().get(1).name());
        assertEquals("172.21.111.11", device.channels().get(1).sourceIp());
        assertEquals(554, device.rtspPort());
    }

    @Test
    void fetchDevicePrefersStreamingChannelsWhenAvailable() throws Exception {
        NvrChannelClient nvr = new NvrChannelClient(stubClient(200, INPUT_PROXY_XML, 200, STREAMING_XML));

        NvrChannelClient.NvrDevice device = nvr.fetchDevice("10.0.0.1", 80, "admin", "pw");

        // Streaming 可用时以 Streaming 为准（仅主码流且 enabled）：101 → 通道 1，201 → 通道 2
        assertEquals(2, device.channels().size());
        assertEquals(1, device.channels().get(0).channel());
        assertEquals(101, device.channels().get(0).trackId());
        assertEquals("Visible Camera", device.channels().get(0).name());
        assertEquals("10.10.0.93", device.channels().get(0).sourceIp());
        assertEquals(2, device.channels().get(1).channel());
        assertEquals(201, device.channels().get(1).trackId());
        assertEquals("Thermal Camera", device.channels().get(1).name());
        assertEquals("10.10.0.94", device.channels().get(1).sourceIp());
    }

    @Test
    void fetchDeviceFailsWhenNeitherStreamingNorInputProxyAvailable() throws Exception {
        NvrChannelClient nvr = new NvrChannelClient(stubClient(403, "", 403, "forbidden"));

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> nvr.fetchDevice("10.0.0.1", 80, "admin", "pw"));
        assertTrue(error.getReason() != null && error.getReason().contains("通道列表读取失败"));
    }
}
