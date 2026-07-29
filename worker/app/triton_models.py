import math
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

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


@dataclass
class ObjectDetection:
    label_id: int
    label_name: str
    score: float
    bbox: np.ndarray


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

RETINAFACE_TEMPLATE = np.array(
    [
        [30.0, 51.0],
        [82.0, 51.0],
        [56.0, 71.0],
        [40.0, 92.0],
        [72.0, 92.0],
    ],
    dtype=np.float32,
)

RETINAFACE_MEAN = np.array([104.0, 117.0, 123.0], dtype=np.float32)
RETINAFACE_VARIANCE = [0.1, 0.2]
RETINAFACE_MIN_SIZES = [[16, 32], [64, 128], [256, 512]]
RETINAFACE_STEPS = [8, 16, 32]


class TritonFaceClient:
    def __init__(self, config: Settings):
        self.config = config
        self.base_url = config.triton_http_url.rstrip("/")
        self.session = requests.Session()
        self._model_config_cache: Dict[str, Dict] = {}

    def extract_embedding(self, image_bgr: np.ndarray) -> List[float]:
        detections = self.detect_faces(image_bgr)
        if len(detections) != 1:
            raise HTTPException(status_code=400, detail=f"expected exactly one face, found {len(detections)}")
        aligned = self.align_detection(image_bgr, detections[0])
        embedding = self.embed(aligned)
        return embedding.tolist()

    def detect_faces(self, image_bgr: np.ndarray) -> List[FaceDetection]:
        if self.config.face_detector == "retinaface":
            return self.detect_faces_retinaface(image_bgr)
        return self.detect_faces_scrfd(image_bgr)

    def detect_faces_scrfd(self, image_bgr: np.ndarray) -> List[FaceDetection]:
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

    def detect_faces_retinaface(self, image_bgr: np.ndarray) -> List[FaceDetection]:
        input_tensor, resize = preprocess_retinaface(image_bgr)
        output_map = {
            "loc": self.config.retinaface_loc_output,
            "cls": self.config.retinaface_cls_output,
            "land": self.config.retinaface_land_output,
        }
        result = self._infer(
            self.config.retinaface_model_name,
            self._input_name(self.config.retinaface_model_name, self.config.retinaface_input_name),
            input_tensor,
            outputs=list(output_map.values()),
        )
        result = {logical: result[actual] for logical, actual in output_map.items()}
        priors = retinaface_priors((640, 640))
        detections = decode_retinaface(result, resize, priors, self.config.retinaface_score_threshold)
        return nms(detections, 0.4)

    def embed(self, aligned_bgr: np.ndarray) -> np.ndarray:
        tensor = preprocess_arcface(aligned_bgr)
        input_name = self._input_name(self.config.arcface_model_name, self.config.arcface_input_name)
        output_name = self._output_names(self.config.arcface_model_name, [self.config.arcface_output_name])[0]
        result = self._infer(
            self.config.arcface_model_name,
            input_name,
            tensor,
            outputs=[output_name],
        )
        embedding = result[output_name].reshape(-1).astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def alignment_template(self) -> np.ndarray:
        if self.config.face_detector == "retinaface":
            return RETINAFACE_TEMPLATE
        return ARC_TEMPLATE

    def align_detection(self, image_bgr: np.ndarray, detection: FaceDetection) -> np.ndarray:
        if self.config.face_detector == "retinaface":
            return align_retinaface(image_bgr, detection.bbox, detection.kps)
        return align_face(image_bgr, detection.kps, ARC_TEMPLATE)

    def _input_name(self, model_name: str, configured: str) -> str:
        if configured and configured.lower() != "auto":
            return configured
        config = self._model_config(model_name)
        inputs = config.get("input") or []
        if not inputs:
            raise RuntimeError(f"Triton model {model_name} has no configured inputs")
        return inputs[0]["name"]

    def _output_names(self, model_name: str, configured: List[str]) -> List[str]:
        if configured and all(name and name.lower() != "auto" for name in configured):
            return configured
        config = self._model_config(model_name)
        outputs = config.get("output") or []
        if not outputs:
            raise RuntimeError(f"Triton model {model_name} has no configured outputs")
        return [outputs[0]["name"]]

    def _model_config(self, model_name: str) -> Dict:
        if model_name not in self._model_config_cache:
            response = self.session.get(f"{self.base_url}/v2/models/{model_name}/config", timeout=10)
            if response.status_code >= 400:
                self._load_model(model_name)
                response = self.session.get(f"{self.base_url}/v2/models/{model_name}/config", timeout=10)
            if response.status_code >= 400:
                raise RuntimeError(response.text)
            self._model_config_cache[model_name] = response.json()
        return self._model_config_cache[model_name]

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
            body = header + tensor_bytes
            headers = {
                "Content-Type": "application/octet-stream",
                "Inference-Header-Content-Length": str(len(header)),
            }
            response = self._infer_request(model_name, body, headers, timeout=30)
            if response.status_code >= 400:
                self._load_model(model_name)
                response = self._infer_request(model_name, body, headers, timeout=30)
            if response.status_code >= 400:
                raise RuntimeError(response.text)
            return parse_triton_binary_response(response, outputs)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Triton inference failed for {model_name}: {exc}") from exc

    def _infer_request(self, model_name: str, body: bytes, headers: Dict[str, str], timeout: int) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/v2/models/{model_name}/infer",
            data=body,
            headers=headers,
            timeout=timeout,
        )

    def _load_model(self, model_name: str) -> None:
        response = self.session.post(
            f"{self.base_url}/v2/repository/models/{quote(model_name, safe='')}/load",
            json={},
            timeout=120,
        )
        if response.status_code >= 400:
            raise RuntimeError(response.text)


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


def preprocess_retinaface(image_bgr: np.ndarray) -> Tuple[np.ndarray, float]:
    height, width = image_bgr.shape[:2]
    target = 640
    resize = float(target) / float(max(height, width))
    resized = cv2.resize(image_bgr, None, None, fx=resize, fy=resize, interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((target, target, 3), dtype=np.float32)
    canvas[: resized.shape[0], : resized.shape[1]] = resized.astype(np.float32)
    canvas -= RETINAFACE_MEAN
    tensor = np.transpose(canvas, (2, 0, 1))[None, :, :, :]
    return np.ascontiguousarray(tensor), resize


def retinaface_priors(image_size: Tuple[int, int]) -> np.ndarray:
    anchors = []
    image_h, image_w = image_size
    feature_maps = [[math.ceil(image_h / step), math.ceil(image_w / step)] for step in RETINAFACE_STEPS]
    for k, feature_map in enumerate(feature_maps):
        min_sizes = RETINAFACE_MIN_SIZES[k]
        for i in range(feature_map[0]):
            for j in range(feature_map[1]):
                for min_size in min_sizes:
                    s_kx = min_size / image_w
                    s_ky = min_size / image_h
                    cx = (j + 0.5) * RETINAFACE_STEPS[k] / image_w
                    cy = (i + 0.5) * RETINAFACE_STEPS[k] / image_h
                    anchors.append([cx, cy, s_kx, s_ky])
    return np.array(anchors, dtype=np.float32)


def decode_retinaface(outputs: Dict[str, np.ndarray], resize: float, priors: np.ndarray, threshold: float) -> List[FaceDetection]:
    loc = outputs["loc"].reshape(-1, 4)
    conf = outputs["cls"].reshape(-1, 2)
    land = outputs["land"].reshape(-1, 10)

    priors = priors[: loc.shape[0]]
    boxes = np.concatenate(
        (
            priors[:, :2] + loc[:, :2] * RETINAFACE_VARIANCE[0] * priors[:, 2:],
            priors[:, 2:] * np.exp(loc[:, 2:] * RETINAFACE_VARIANCE[1]),
        ),
        axis=1,
    )
    boxes[:, :2] -= boxes[:, 2:] / 2
    boxes[:, 2:] += boxes[:, :2]
    boxes *= np.array([640, 640, 640, 640], dtype=np.float32)
    boxes /= resize

    landmarks = np.concatenate(
        (
            priors[:, :2] + land[:, :2] * RETINAFACE_VARIANCE[0] * priors[:, 2:],
            priors[:, :2] + land[:, 2:4] * RETINAFACE_VARIANCE[0] * priors[:, 2:],
            priors[:, :2] + land[:, 4:6] * RETINAFACE_VARIANCE[0] * priors[:, 2:],
            priors[:, :2] + land[:, 6:8] * RETINAFACE_VARIANCE[0] * priors[:, 2:],
            priors[:, :2] + land[:, 8:10] * RETINAFACE_VARIANCE[0] * priors[:, 2:],
        ),
        axis=1,
    )
    landmarks *= np.array([640, 640, 640, 640, 640, 640, 640, 640, 640, 640], dtype=np.float32)
    landmarks /= resize

    scores = conf[:, 1]
    keep = np.where(scores >= threshold)[0]
    detections: List[FaceDetection] = []
    for index in keep:
        detections.append(
            FaceDetection(
                bbox=boxes[index].astype(np.float32),
                kps=landmarks[index].reshape(5, 2).astype(np.float32),
                score=float(scores[index]),
            )
        )
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


def align_face(image_bgr: np.ndarray, landmarks: np.ndarray, template: np.ndarray = ARC_TEMPLATE) -> np.ndarray:
    transform, _ = cv2.estimateAffinePartial2D(landmarks.astype(np.float32), template, method=cv2.LMEDS)
    if transform is None:
        raise HTTPException(status_code=400, detail="failed to align face")
    return cv2.warpAffine(image_bgr, transform, (112, 112), borderValue=0.0)


def align_retinaface(image_bgr: np.ndarray, bbox: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
    height, width = image_bgr.shape[:2]
    x1, y1, x2, y2 = bbox[:4].astype(np.int32)
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(x1 + 1, min(width, x2))
    y2 = max(y1 + 1, min(height, y2))
    cropped = image_bgr[y1:y2, x1:x2]
    if cropped.size == 0:
        raise HTTPException(status_code=400, detail="invalid face crop")

    resized = cv2.resize(cropped, (112, 112), interpolation=cv2.INTER_CUBIC)
    relative = landmarks.astype(np.float32) - np.array([x1, y1], dtype=np.float32)
    scale = np.array([112.0 / (x2 - x1), 112.0 / (y2 - y1)], dtype=np.float32)
    resized_landmarks = relative * scale
    transform, _ = cv2.estimateAffinePartial2D(resized_landmarks, RETINAFACE_TEMPLATE)
    if transform is None:
        raise HTTPException(status_code=400, detail="failed to align face")
    return cv2.warpAffine(resized, transform, (112, 112), borderMode=cv2.BORDER_REPLICATE)


def preprocess_arcface(image_bgr: np.ndarray) -> np.ndarray:
    resized = cv2.resize(image_bgr, (112, 112))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32)
    rgb = (rgb - 127.5) / 127.5
    tensor = np.transpose(rgb, (2, 0, 1))[None, :, :, :]
    return np.ascontiguousarray(tensor)


COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]

BOX_COLORS = [
    (0, 0, 255), (255, 0, 20), (0, 255, 0), (170, 170, 20),
    (255, 128, 0), (0, 128, 255), (128, 0, 255), (255, 255, 0),
    (0, 255, 255), (255, 0, 255),
]


class DinoDetectionClient:
    def __init__(self, config: Settings):
        self.config = config
        self.base_url = config.dino_triton_http_url.rstrip("/")
        self.session = requests.Session()
        self.labels = config.dino_labels if hasattr(config, "dino_labels") else COCO_LABELS

    def preprocess(self, image_bgr: np.ndarray):
        height, width = image_bgr.shape[:2]
        target = self.config.dino_target_size
        target_h, target_w = target[0], target[1]
        im_size_min, im_size_max = min(height, width), max(height, width)
        target_min, target_max = min(target_h, target_w), max(target_h, target_w)
        im_scale = float(target_min) / float(im_size_min)
        if np.round(im_scale * im_size_max) > target_max:
            im_scale = float(target_max) / float(im_size_max)
        resized = cv2.resize(image_bgr, None, None, fx=im_scale, fy=im_scale, interpolation=cv2.INTER_LINEAR)
        img_float = resized[..., ::-1].astype(np.float32) * (1.0 / 255.0)
        mean = np.array(self.config.dino_mean, dtype=np.float32)
        std = np.array(self.config.dino_std, dtype=np.float32)
        normalized = (img_float - mean) / std
        img_chw = np.ascontiguousarray(np.transpose(normalized, (2, 0, 1)))
        image = img_chw[np.newaxis, ...]
        im_shape = np.array(img_chw.shape[1:], dtype=np.float32).reshape(1, 2)
        scale_factor = np.array([im_scale, im_scale], dtype=np.float32).reshape(1, 2)
        return image, im_shape, scale_factor, (height, width)

    def detect_objects(self, image_bgr: np.ndarray) -> List[ObjectDetection]:
        image, im_shape, scale_factor, _ = self.preprocess(image_bgr)
        result = self._infer(image, im_shape, scale_factor)
        outputs = result[self.config.dino_output_0].reshape(-1, 6)
        detections = []
        conf_thres = self.config.dino_conf_thres
        for row in outputs:
            label_id, score, x1, y1, x2, y2 = row
            if score < conf_thres:
                continue
            label_id = int(label_id)
            label_name = self.labels[label_id] if label_id < len(self.labels) else str(label_id)
            detections.append(ObjectDetection(
                label_id=label_id,
                label_name=label_name,
                score=float(score),
                bbox=np.array([x1, y1, x2, y2], dtype=np.float32),
            ))
        return detections

    def _infer(self, image: np.ndarray, im_shape: np.ndarray, scale_factor: np.ndarray) -> Dict[str, np.ndarray]:
        try:
            image_bytes = image.tobytes(order="C")
            im_shape_bytes = im_shape.tobytes(order="C")
            scale_factor_bytes = scale_factor.tobytes(order="C")

            request_payload = {
                "inputs": [
                    {
                        "name": self.config.dino_image_input,
                        "shape": list(image.shape),
                        "datatype": "FP32",
                        "parameters": {"binary_data_size": len(image_bytes)},
                    },
                    {
                        "name": self.config.dino_imshape_input,
                        "shape": list(im_shape.shape),
                        "datatype": "FP32",
                        "parameters": {"binary_data_size": len(im_shape_bytes)},
                    },
                    {
                        "name": self.config.dino_scalefactor_input,
                        "shape": list(scale_factor.shape),
                        "datatype": "FP32",
                        "parameters": {"binary_data_size": len(scale_factor_bytes)},
                    },
                ],
                "outputs": [
                    {"name": self.config.dino_output_0, "parameters": {"binary_data": True}},
                    {"name": self.config.dino_output_1, "parameters": {"binary_data": True}},
                ],
            }
            header = json.dumps(request_payload).encode("utf-8")
            body = header + image_bytes + im_shape_bytes + scale_factor_bytes
            headers = {
                "Content-Type": "application/octet-stream",
                "Inference-Header-Content-Length": str(len(header)),
            }
            response = self._infer_request(body, headers)
            if response.status_code >= 400:
                self._load_model()
                response = self._infer_request(body, headers)
            if response.status_code >= 400:
                raise RuntimeError(response.text)
            return parse_triton_binary_response(
                response,
                [self.config.dino_output_0, self.config.dino_output_1],
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"DINO Triton inference failed: {exc}") from exc

    def _infer_request(self, body: bytes, headers: Dict[str, str]) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/v2/models/{self.config.dino_model_name}/infer",
            data=body,
            headers=headers,
            timeout=120,
        )

    def _load_model(self) -> None:
        response = self.session.post(
            f"{self.base_url}/v2/repository/models/{quote(self.config.dino_model_name, safe='')}/load",
            json={},
            timeout=180,
        )
        if response.status_code >= 400:
            raise RuntimeError(response.text)


def draw_object_boxes(frame: np.ndarray, detections: List[ObjectDetection], conf_thres: float = 0.3) -> np.ndarray:
    for det in detections:
        if det.score < conf_thres:
            continue
        x1, y1, x2, y2 = det.bbox.astype(int)
        color_idx = det.label_id % len(BOX_COLORS)
        color = BOX_COLORS[color_idx]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{det.label_name}: {det.score:.2f}"
        cv2.putText(frame, label, (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
    return frame
