package com.videoai.monitoring.core.support;

import com.videoai.monitoring.core.support.Gb28181CatalogClient.Gb28181CatalogDevice;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class Gb28181CatalogClientTest {

    // --- Digest（RFC 2617 已知向量） ---

    @Test
    void digestResponseMatchesRfc2617VectorWithoutQop() {
        // RFC 2617 示例：Mufasa / Circle Of Life / testrealm@host.com
        String response = Gb28181CatalogClient.digestResponse(
                "Mufasa", "Circle Of Life", "testrealm@host.com",
                "dcd98b7102dd2f0e8b11d0f600bfb0c093",
                null, null, null, "GET", "/dir/index.html");

        assertEquals("670fd8c2df070c60b045671b8b24ff02", response);
    }

    @Test
    void digestResponseMatchesRfc2617VectorWithQopAuth() {
        String response = Gb28181CatalogClient.digestResponse(
                "Mufasa", "Circle Of Life", "testrealm@host.com",
                "dcd98b7102dd2f0e8b11d0f600bfb0c093",
                "auth", "00000001", "0a4f113b", "GET", "/dir/index.html");

        assertEquals("6629fae49393a05397450978507c4ef1", response);
    }

    @Test
    void parseDigestChallengeExtractsRealmNonceAndQop() {
        Map<String, String> challenge = Gb28181CatalogClient.parseDigestChallenge(
                "Digest realm=\"34020000\", nonce=\"abc123,def\", qop=\"auth\", algorithm=MD5");

        assertEquals("34020000", challenge.get("realm"));
        // nonce 内含逗号：不能按逗号简单切分
        assertEquals("abc123,def", challenge.get("nonce"));
        assertEquals("auth", challenge.get("qop"));
        assertEquals("MD5", challenge.get("algorithm"));
    }

    @Test
    void buildDigestAuthorizationProducesHeaderWithResponse() {
        String header = Gb28181CatalogClient.buildDigestAuthorization(
                "Digest realm=\"testrealm@host.com\", nonce=\"dcd98b7102dd2f0e8b11d0f600bfb0c093\"",
                "Mufasa", "Circle Of Life", "MESSAGE", "sip:34020000002000000001@192.168.1.10:5060");

        assertTrue(header.startsWith("Digest "));
        assertTrue(header.contains("username=\"Mufasa\""));
        assertTrue(header.contains("realm=\"testrealm@host.com\""));
        assertTrue(header.contains("uri=\"sip:34020000002000000001@192.168.1.10:5060\""));
        // 无 qop 时 response = MD5(HA1:nonce:HA2)，可精确比对
        String expected = Gb28181CatalogClient.digestResponse(
                "Mufasa", "Circle Of Life", "testrealm@host.com",
                "dcd98b7102dd2f0e8b11d0f600bfb0c093",
                null, null, null, "MESSAGE", "sip:34020000002000000001@192.168.1.10:5060");
        assertTrue(header.contains("response=\"" + expected + "\""));
    }

    // --- Catalog XML 解析 ---

    private static final String SAMPLE_XML = """
            <?xml version="1.0" encoding="GB2312"?>
            <Response>
            <CmdType>Catalog</CmdType>
            <SN>248219</SN>
            <DeviceID>34020000001320000001</DeviceID>
            <SumNum>2</SumNum>
            <DeviceList Num="2">
            <Item>
            <DeviceID>34020000001320000101</DeviceID>
            <Name>北门摄像头</Name>
            <Manufacturer>Hikvision</Manufacturer>
            <Model>DS-2CD</Model>
            <Owner>OwnerA</Owner>
            <ParentId>34020000001320000001</ParentId>
            </Item>
            <Item>
            <DeviceID>34020000001320000102</DeviceID>
            <Name>东门摄像头</Name>
            <Manufacturer>Dahua</Manufacturer>
            </Item>
            </DeviceList>
            </Response>
            """;

    @Test
    void parseCatalogResponseExtractsSumNumAndItems() {
        Gb28181CatalogClient.CatalogPage page = Gb28181CatalogClient.parseCatalogResponse(SAMPLE_XML);

        assertEquals(2, page.sumNum());
        assertEquals(2, page.items().size());
        Gb28181CatalogDevice first = page.items().get(0);
        assertEquals("34020000001320000101", first.deviceId());
        assertEquals("北门摄像头", first.name());
        assertEquals("Hikvision", first.manufacturer());
        assertEquals("DS-2CD", first.model());
        assertEquals("OwnerA", first.owner());
        assertEquals("34020000001320000001", first.parentId());
        // 缺失的可选字段为 null
        Gb28181CatalogDevice second = page.items().get(1);
        assertEquals("34020000001320000102", second.deviceId());
        assertNull(second.model());
        assertNull(second.owner());
    }

    @Test
    void parseCatalogResponseHandlesEmptyDeviceList() {
        Gb28181CatalogClient.CatalogPage page = Gb28181CatalogClient.parseCatalogResponse("""
                <?xml version="1.0" encoding="GB2312"?>
                <Response>
                <CmdType>Catalog</CmdType>
                <SN>1</SN>
                <DeviceID>34020000001320000001</DeviceID>
                <SumNum>0</SumNum>
                <DeviceList Num="0">
                </DeviceList>
                </Response>
                """);

        assertEquals(0, page.sumNum());
        assertEquals(List.of(), page.items());
    }
}
