"""Minimal ImageNet preprocess for Space distillation (vendored from app/preprocessing)."""

from __future__ import annotations

from PIL import Image

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def to_model_input(image: Image.Image, size: int = 224, crop_pct: float = 0.875):
    """Resize / center-crop / normalize → NCHW float32 (1, 3, H, W)."""
    import numpy as np

    resize_to = int(size / crop_pct)  # 256
    w, h = image.size
    if w <= h:
        new_w, new_h = resize_to, int(resize_to * h / w)
    else:
        new_w, new_h = int(resize_to * w / h), resize_to
    resized = image.resize((new_w, new_h), resample=Image.Resampling.BICUBIC)
    left, top = (new_w - size) // 2, (new_h - size) // 2
    cropped = resized.crop((left, top, left + size, top + size))

    arr = np.asarray(cropped, dtype=np.float32) / 255.0
    arr = (arr - np.array(IMAGENET_MEAN, dtype=np.float32)) / np.array(
        IMAGENET_STD, dtype=np.float32
    )
    return np.ascontiguousarray(arr.transpose(2, 0, 1)[None, ...])
