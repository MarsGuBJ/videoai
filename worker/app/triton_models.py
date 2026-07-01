import math
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

import cv2
import numpy as np
import requests
from fastapi import HTTPException

from .config import Settings


@dataclass
class FaceDetection:
    bbox: np.ndarray
    kps: np.ndarray
    score: float


ARC_TEMPLATE = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


class TritonFaceClient:
    def __init__(self, config: Settings):
        self.config = config
        self.base_url = config.triton_http_url.rstrip("/")
        self.session = requests.Session()

    def extract_embedding(self, image_bgr: np.ndarray) -> List[float]:
        detections = self.detect_faces(image_bgr)
        if len(detections) != 1:
            raise HTTPException(status_code=400, detail=f"expected exactly one face, found {len(detections)}")
        aligned = align_face(image_bgr, detections[0].kps)
        embedding = self.embed(aligned)
        return embedding.tolist()

    def detect_faces(self, image_bgr: np.ndarray) -> List[FaceDetection]:
        input_tensor, ratio, pad = preprocess_scrfd(image_bgr)
        output_map = {
            "score_8": self.config.scrfd_score_8_output,
            "score_16": self.config.scrfd_score_16_output,
            "score_32": self.config.scrfd_score_32_output,
            "bbox_8": self.config.scrfd_bbox_8_output,
            "bbox_16": self.config.scrfd_bbox_16_output,
            "bbox_32": self.config.scrfd_bbox_32_output,
            "kps_8": self.config.scrfd_kps_8_output,
            "kps_16": self.config.scrfd_kps_16_output,
            "kps_32": self.config.scrfd_kps_32_output,
        }
        result = self._infer(
            self.config.scrfd_model_name,
            self.config.scrfd_input_name,
            input_tensor,
            outputs=list(output_map.values()),
        )
        result = {logical: result[actual] for logical, actual in output_map.items()}
        detections = decode_scrfd(result, ratio, pad)
        return nms(detections, 0.4)

    def embed(self, aligned_bgr: np.ndarray) -> np.ndarray:
        tensor = preprocess_arcface(aligned_bgr)
        result = self._infer(
            self.config.arcface_model_name,
            self.config.arcface_input_name,
            tensor,
            outputs=[self.config.arcface_output_name],
        )
        embedding = result[self.config.arcface_output_name].reshape(-1).astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def _infer(self, model_name: str, input_name: str, tensor: np.ndarray, outputs: List[str]) -> Dict[str, np.ndarray]:
        try:
            tensor = np.ascontiguousarray(tensor.astype(np.float32, copy=False))
            tensor_bytes = tensor.tobytes(order="C")
            request = {
                "inputs": [
                    {
                        "name": input_name,
                        "shape": list(tensor.shape),
                        "datatype": "FP32",
                        "parameters": {"binary_data_size": len(tensor_bytes)},
                    }
                ],
                "outputs": [{"name": output, "parameters": {"binary_data": True}} for output in outputs],
            }
            header = json.dumps(request).encode("utf-8")
            response = self.session.post(
                f"{self.base_url}/v2/models/{model_name}/infer",
                data=header + tensor_bytes,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Inference-Header-Content-Length": str(len(header)),
                },
                timeout=30,
            )
            if response.status_code >= 400:
                raise RuntimeError(response.text)
            return parse_triton_binary_response(response, outputs)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Triton inference failed for {model_name}: {exc}") from exc


def parse_triton_binary_response(response: requests.Response, expected_outputs: List[str]) -> Dict[str, np.ndarray]:
    header_length = int(response.headers.get("Inference-Header-Content-Length", "0"))
    if header_length <= 0:
        return parse_triton_json_response(response.json(), expected_outputs)

    content = response.content
    metadata = json.loads(content[:header_length])
    binary = memoryview(content)[header_length:]
    offset = 0
    outputs: Dict[str, np.ndarray] = {}
    for output in metadata.get("outputs", []):
        name = output["name"]
        dtype = triton_dtype_to_numpy(output["datatype"])
        shape = output["shape"]
        size = int(output.get("parameters", {}).get("binary_data_size", 0))
        if size <= 0:
            continue
        values = np.frombuffer(binary[offset : offset + size], dtype=dtype).copy()
        outputs[name] = values.reshape(shape)
        offset += size
    missing = [output for output in expected_outputs if output not in outputs]
    if missing:
        raise RuntimeError(f"missing Triton outputs: {', '.join(missing)}")
    return outputs


def parse_triton_json_response(metadata: Dict, expected_outputs: List[str]) -> Dict[str, np.ndarray]:
    outputs: Dict[str, np.ndarray] = {}
    for output in metadata.get("outputs", []):
        if "data" not in output:
            continue
        dtype = triton_dtype_to_numpy(output["datatype"])
        outputs[output["name"]] = np.array(output["data"], dtype=dtype).reshape(output["shape"])
    missing = [output for output in expected_outputs if output not in outputs]
    if missing:
        raise RuntimeError(f"missing Triton outputs: {', '.join(missing)}")
    return outputs


def triton_dtype_to_numpy(datatype: str) -> np.dtype:
    mapping = {
        "BOOL": np.bool_,
        "UINT8": np.uint8,
        "UINT16": np.uint16,
        "UINT32": np.uint32,
        "UINT64": np.uint64,
        "INT8": np.int8,
        "INT16": np.int16,
        "INT32": np.int32,
        "INT64": np.int64,
        "FP16": np.float16,
        "FP32": np.float32,
        "FP64": np.float64,
    }
    if datatype not in mapping:
        raise RuntimeError(f"unsupported Triton datatype: {datatype}")
    return np.dtype(mapping[datatype])


def preprocess_scrfd(image_bgr: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    height, width = image_bgr.shape[:2]
    target = 640
    ratio = min(target / width, target / height)
    resized_w = int(width * ratio)
    resized_h = int(height * ratio)
    resized = cv2.resize(image_bgr, (resized_w, resized_h))
    canvas = np.zeros((target, target, 3), dtype=np.uint8)
    pad_x = (target - resized_w) // 2
    pad_y = (target - resized_h) // 2
    canvas[pad_y : pad_y + resized_h, pad_x : pad_x + resized_w] = resized
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32)
    rgb = (rgb - 127.5) / 128.0
    tensor = np.transpose(rgb, (2, 0, 1))[None, :, :, :]
    return np.ascontiguousarray(tensor), ratio, (pad_x, pad_y)


def decode_scrfd(outputs: Dict[str, np.ndarray], ratio: float, pad: Tuple[int, int]) -> List[FaceDetection]:
    detections: List[FaceDetection] = []
    input_size = 640
    score_threshold = 0.5
    pad_x, pad_y = pad
    for stride in (8, 16, 32):
        scores = outputs[f"score_{stride}"].reshape(-1)
        boxes = outputs[f"bbox_{stride}"].reshape(-1, 4)
        kps = outputs[f"kps_{stride}"].reshape(-1, 10)
        height = math.ceil(input_size / stride)
        width = math.ceil(input_size / stride)
        anchors = np.stack(np.meshgrid(np.arange(width), np.arange(height)), axis=-1).reshape(-1, 2)
        anchors = np.repeat(anchors, 2, axis=0)[: scores.shape[0]]
        keep = np.where(scores >= score_threshold)[0]
        for index in keep:
            anchor = anchors[index].astype(np.float32)
            distance = boxes[index]
            x1 = (anchor[0] - distance[0]) * stride
            y1 = (anchor[1] - distance[1]) * stride
            x2 = (anchor[0] + distance[2]) * stride
            y2 = (anchor[1] + distance[3]) * stride
            bbox = np.array([(x1 - pad_x) / ratio, (y1 - pad_y) / ratio, (x2 - pad_x) / ratio, (y2 - pad_y) / ratio], dtype=np.float32)
            points = []
            for i in range(5):
                px = (anchor[0] + kps[index][i * 2]) * stride
                py = (anchor[1] + kps[index][i * 2 + 1]) * stride
                points.append([(px - pad_x) / ratio, (py - pad_y) / ratio])
            detections.append(FaceDetection(bbox=bbox, kps=np.array(points, dtype=np.float32), score=float(scores[index])))
    return detections


def nms(detections: List[FaceDetection], threshold: float) -> List[FaceDetection]:
    if not detections:
        return []
    boxes = np.array([d.bbox for d in detections])
    scores = np.array([d.score for d in detections])
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        intersection = w * h
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_rest = (boxes[order[1:], 2] - boxes[order[1:], 0]) * (boxes[order[1:], 3] - boxes[order[1:], 1])
        iou = intersection / (area_i + area_rest - intersection + 1e-6)
        order = order[np.where(iou <= threshold)[0] + 1]
    return [detections[i] for i in keep]


def align_face(image_bgr: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
    transform, _ = cv2.estimateAffinePartial2D(landmarks.astype(np.float32), ARC_TEMPLATE, method=cv2.LMEDS)
    if transform is None:
        raise HTTPException(status_code=400, detail="failed to align face")
    return cv2.warpAffine(image_bgr, transform, (112, 112), borderValue=0.0)


def preprocess_arcface(image_bgr: np.ndarray) -> np.ndarray:
    resized = cv2.resize(image_bgr, (112, 112))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32)
    rgb = (rgb - 127.5) / 127.5
    tensor = np.transpose(rgb, (2, 0, 1))[None, :, :, :]
    return np.ascontiguousarray(tensor)
