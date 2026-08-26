"""内嵌 OpenCV 子进程脚本（经 ``sys.executable -c`` 执行）。

从原 main.py 内联字符串原样提取为模块常量，内容逐字节保持，
以免改变人脸检测/相似度的行为。
"""

DETECT_FACE_REGIONS_SCRIPT = """
import sys
try:
    import cv2
    import numpy as np
except Exception:
    sys.exit(2)
data = sys.stdin.buffer.read()
image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
if image is None:
    sys.exit(1)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
variants = [
    gray,
    cv2.equalizeHist(gray),
    cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray),
]
cascade_names = [
    "haarcascade_frontalface_alt.xml",
    "haarcascade_frontalface_alt2.xml",
    "haarcascade_frontalface_default.xml",
]
boxes = []
height, width = gray.shape[:2]
min_size = max(40, min(width, height) // 14)
for cascade_name in cascade_names:
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_name)
    if cascade.empty():
        continue
    for variant in variants:
        for scale in (1.03, 1.05, 1.08, 1.1):
            faces = cascade.detectMultiScale(
                variant,
                scaleFactor=scale,
                minNeighbors=2,
                minSize=(min_size, min_size),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            for x, y, w, h in faces:
                if w * h < min_size * min_size:
                    continue
                boxes.append((int(x), int(y), int(w), int(h)))
            if boxes:
                break
        if boxes:
            break
    if boxes:
        break

def iou(a, b):
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0

merged = []
for box in sorted(boxes, key=lambda item: item[2] * item[3], reverse=True):
    if all(iou(box, kept) < 0.35 for kept in merged):
        merged.append(box)

sys.stdout.buffer.write(len(merged).to_bytes(2, "big"))
for x, y, w, h in merged[:5]:
    pad = int(max(w, h) * 0.25)
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(width, x + w + pad)
    y2 = min(height, y + h + pad)
    crop = image[y1:y2, x1:x2]
    ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        sys.stdout.buffer.write((0).to_bytes(4, "big"))
        continue
    raw = encoded.tobytes()
    sys.stdout.buffer.write(len(raw).to_bytes(4, "big"))
    sys.stdout.buffer.write(raw)
"""

IMAGE_SIMILARITY_SCRIPT = """
import sys
try:
    import cv2
    import numpy as np
except Exception:
    sys.exit(3)
frame_path, face_path = sys.argv[1], sys.argv[2]
frame = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
face = cv2.imread(face_path, cv2.IMREAD_GRAYSCALE)
if frame is None or face is None:
    sys.exit(2)
def hist(image):
    resized = cv2.resize(image, (128, 128))
    equalized = cv2.equalizeHist(resized)
    value = cv2.calcHist([equalized], [0], None, [64], [0, 256])
    cv2.normalize(value, value)
    return value
score = cv2.compareHist(hist(frame), hist(face), cv2.HISTCMP_CORREL)
print(max(0.0, min(1.0, (float(score) + 1.0) / 2.0)))
"""
