"""triton_models 纯函数测试：dtype 映射、JSON 响应解析与 NMS，不触达 Triton 服务。"""

import numpy as np
import pytest

from app.triton_models import FaceDetection, nms, parse_triton_json_response, triton_dtype_to_numpy


def test_triton_dtype_to_numpy_maps_known_types():
    assert triton_dtype_to_numpy("FP32") == np.dtype(np.float32)
    assert triton_dtype_to_numpy("INT32") == np.dtype(np.int32)
    assert triton_dtype_to_numpy("UINT8") == np.dtype(np.uint8)


def test_triton_dtype_to_numpy_rejects_unknown_datatype():
    with pytest.raises(RuntimeError, match="unsupported Triton datatype"):
        triton_dtype_to_numpy("FP8")


def test_parse_triton_json_response_reshapes_named_outputs():
    metadata = {
        "outputs": [
            {"name": "out", "datatype": "FP32", "shape": [1, 2], "data": [1.0, 2.0]},
        ]
    }

    outputs = parse_triton_json_response(metadata, ["out"])

    assert outputs["out"].shape == (1, 2)
    assert outputs["out"].dtype == np.float32
    np.testing.assert_array_equal(outputs["out"], [[1.0, 2.0]])

    with pytest.raises(RuntimeError, match="missing Triton outputs"):
        parse_triton_json_response(metadata, ["out", "other"])


def test_nms_suppresses_overlapping_lower_score_detection():
    def detection(box, score):
        return FaceDetection(
            bbox=np.array(box, dtype=np.float32),
            kps=np.zeros((5, 2), dtype=np.float32),
            score=score,
        )

    kept = nms(
        [
            detection([0, 0, 10, 10], 0.9),
            detection([1, 1, 11, 11], 0.8),
            detection([100, 100, 110, 110], 0.7),
        ],
        threshold=0.4,
    )

    assert [item.score for item in kept] == [0.9, 0.7]
