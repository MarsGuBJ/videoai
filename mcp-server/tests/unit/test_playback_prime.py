"""起播 primer 的 PS 关键帧定位测试：find_first_video_idr。"""
from app.hcnetsdk_playback import find_first_video_idr


def pes(stream_id: int, payload: bytes, pkt_len: int | None = None) -> bytes:
    """构造一个 PES 包（flags=0x8000，无扩展头）。"""
    length = len(payload) + 3 if pkt_len is None else pkt_len
    return b"\x00\x00\x01" + bytes([stream_id]) + length.to_bytes(2, "big") + b"\x80\x00\x00" + payload


def pack(body: bytes) -> bytes:
    """构造一个极简 PS pack（仅起始码 + 占位字节，扫描器只依赖起始码定位）。"""
    return b"\x00\x00\x01\xba" + b"\x00" * 8 + body


def nal(b0: int, payload: bytes = b"\x11\x22\x33") -> bytes:
    return b"\x00\x00\x01" + bytes([b0]) + payload


def test_h264_idr_found() -> None:
    buf = pack(pes(0xE0, nal(0x61) + nal(0x65)))  # 非 IDR + IDR(type=5)
    assert find_first_video_idr(buf) == 12  # pack 起始码4 + 占位8 = 12


def test_hevc_idr_found() -> None:
    buf = pack(pes(0xE0, nal(0x02) + nal(0x26)))  # 非 IDR + H.265 IDR_W_RADL(type=19)
    assert find_first_video_idr(buf) == 12


def test_hevc_cra_found() -> None:
    buf = pack(pes(0xE0, nal(0x2A)))  # H.265 CRA(type=21) 也作为干净起点
    assert find_first_video_idr(buf) == 12


def test_no_idr_returns_none() -> None:
    buf = pack(pes(0xE0, nal(0x61) + nal(0x41) + nal(0x06)))
    assert find_first_video_idr(buf) is None


def test_returns_idr_pes_not_first_pes() -> None:
    first = pes(0xE0, nal(0x61))
    second = pes(0xE0, nal(0x65))
    buf = first + second
    assert find_first_video_idr(buf) == len(first)


def test_unbounded_pes_bounded_by_next_pack() -> None:
    """pkt_len=0 的 PES 以下一个 pack 起始码为界，IDR 在后续 pack 时不得提前返回。"""
    first = pack(pes(0xE0, nal(0x61), pkt_len=0))
    second = pack(pes(0xE0, nal(0x65), pkt_len=0))
    buf = first + second
    assert find_first_video_idr(buf) == len(first) + 12


def test_idr_across_chunk_boundary() -> None:
    """NAL 起始码被截断时不误判，数据补齐后返回正确偏移。"""
    full = pack(pes(0xE0, nal(0x65)))
    cut = 23  # 截断在 NAL 起始码中间（pack 12 + PES 头 9 + 起始码 2/4）
    assert find_first_video_idr(full[:cut]) is None
    assert find_first_video_idr(full) == 12


def test_pes_with_extension_header() -> None:
    """PES 头带扩展字段（header_len>0）时从正确载荷位置识别 IDR。"""
    payload = nal(0x65)
    header = b"\x00\x00\x01\xe0" + (len(payload) + 5).to_bytes(2, "big") + b"\x80\x00\x02" + b"\x00\x00"
    buf = header + payload
    assert find_first_video_idr(buf) == 0


def test_empty_and_garbage() -> None:
    assert find_first_video_idr(b"") is None
    assert find_first_video_idr(b"\x00\x00\x01\xba" + b"\xff" * 100) is None


def test_h265_param_pes_before_idr_included() -> None:
    """VPS/SPS/PPS 各占 IDR 前一个独立 PES（现场 smart265 设备实测布局）时，起点回溯到 VPS。"""
    vps = pes(0xE0, nal(0x40))  # H.265 VPS type=32
    sps = pes(0xE0, nal(0x42))  # H.265 SPS type=33
    pps = pes(0xE0, nal(0x44))  # H.265 PPS type=34
    idr = pes(0xE0, nal(0x26))  # H.265 IDR_W_RADL type=19
    buf = pack(vps + sps + pps + idr)
    assert find_first_video_idr(buf) == 12


def test_h264_sps_pps_before_idr_included() -> None:
    """H.264 的 SPS/PPS 在 IDR 前的独立 PES 时同样回溯保留。"""
    sps = pes(0xE0, nal(0x67))  # H.264 SPS type=7
    pps = pes(0xE0, nal(0x68))  # H.264 PPS type=8
    idr = pes(0xE0, nal(0x65))  # H.264 IDR type=5
    buf = sps + pps + idr
    assert find_first_video_idr(buf) == 0


def test_backtrack_stops_at_vcl_pes() -> None:
    """参数集 PES 之前还有上一 GOP 的帧数据时，不回溯越过含 VCL 的 PES。"""
    vcl = pes(0xE0, nal(0x02))  # H.265 非 IDR 帧 type=1
    sps = pes(0xE0, nal(0x42))
    idr = pes(0xE0, nal(0x26))
    buf = vcl + sps + idr
    assert find_first_video_idr(buf) == len(vcl)
