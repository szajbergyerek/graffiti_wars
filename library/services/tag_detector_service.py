import io

import numpy as np
import onnxruntime as ort
from PIL import Image as PILImage
from PIL import ImageOps

MODEL_INPUT_SIZE = 640
LETTERBOX_FILL_COLOR = (114, 114, 114)


class TagDetectorService:
    """
    Runs the same single-class ("Tags") YOLOv8n detection model used
    client-side (onnxruntime-web, to gate the camera shutter) server-side via
    onnxruntime, so a submission can't skip the "is there actually a tag in
    this photo" check by disabling JavaScript or tampering with the client.

    Preprocessing (letterbox resize to 640x640, gray padding, RGB, [0, 1]
    normalization) and postprocessing (single highest-confidence anchor, no
    NMS needed since there's only one class) mirror the client-side
    implementation in tag_submit_upload.html exactly, so a photo that passes
    the client-side gate also passes this one.
    """

    def __init__(self, model_path: str) -> None:
        """
        Load the ONNX tag detector.

        param model_path: Path to the tag_detector.onnx file on disk.

        :return: None.
        """
        self._session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self._input_name = self._session.get_inputs()[0].name

    def detect(self, image_bytes: bytes, conf_threshold: float = 0.5) -> dict | None:
        """
        Run tag detection on raw, encoded image bytes.

        param image_bytes: The raw, encoded (e.g. JPEG) image content.
        param conf_threshold: Minimum confidence to consider a tag detected.

        :return: None if no tag was detected above the threshold, otherwise
            a dict with "confidence" (float) and "box" (an (x1, y1, x2, y2)
            tuple in the original image's own pixel coordinates).
        """
        image = PILImage.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        image_width, image_height = image.size

        padded, scale, pad_x, pad_y = self._letterbox(image)
        pixels = np.asarray(padded, dtype=np.float32) / 255.0
        batched = pixels.transpose(2, 0, 1)[None, ...]

        output = self._session.run(None, {self._input_name: batched})[0]
        predictions = output[0]  # (5, num_anchors): cx, cy, w, h, confidence rows

        confidences = predictions[4]
        best_index = int(np.argmax(confidences))
        best_confidence = float(confidences[best_index])
        if best_confidence < conf_threshold:
            return None

        center_x, center_y, box_w, box_h = (float(v) for v in predictions[0:4, best_index])
        box = (
            max(0.0, (center_x - box_w / 2 - pad_x) / scale),
            max(0.0, (center_y - box_h / 2 - pad_y) / scale),
            min(float(image_width), (center_x + box_w / 2 - pad_x) / scale),
            min(float(image_height), (center_y + box_h / 2 - pad_y) / scale),
        )
        return {"confidence": best_confidence, "box": box}

    def _letterbox(self, image: "PILImage.Image", target_size: int = MODEL_INPUT_SIZE) -> tuple:
        """
        Resize an image to fit within target_size x target_size while
        preserving aspect ratio, padding the rest with the model's expected
        gray fill - matches the client-side canvas letterbox exactly.

        param image: A PIL RGB image.
        param target_size: The model's expected square input size, in pixels.

        :return: A (padded_image, scale, pad_x, pad_y) tuple - scale is the
            resize factor applied, and pad_x/pad_y are the padding added on
            the left/top, both needed to map a detection back to the
            original image's coordinates.
        """
        width, height = image.size
        scale = min(target_size / width, target_size / height)
        resized_w, resized_h = round(width * scale), round(height * scale)
        resized = image.resize((resized_w, resized_h), PILImage.Resampling.BILINEAR)

        padded = PILImage.new("RGB", (target_size, target_size), LETTERBOX_FILL_COLOR)
        pad_x = (target_size - resized_w) // 2
        pad_y = (target_size - resized_h) // 2
        padded.paste(resized, (pad_x, pad_y))
        return padded, scale, pad_x, pad_y
