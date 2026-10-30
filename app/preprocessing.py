"""Validation des images reçues, entièrement en mémoire.

Le type réel du fichier est déterminé à partir de son contenu (décodage Pillow),
pas à partir de l'extension ni du Content-Type annoncé par le client.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

# Format Pillow -> type MIME accepté
PIL_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

# Protection contre les "decompression bombs" (images minuscules en octets
# mais gigantesques une fois décodées).
Image.MAX_IMAGE_PIXELS = 40_000_000


class ImageValidationError(Exception):
    """Erreur de validation, porteuse du code HTTP à renvoyer."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass
class ValidatedImage:
    image: Image.Image  # image décodée, convertie en RGB
    mime_type: str
    size_bytes: int
    width: int
    height: int


def validate_image(data: bytes, max_bytes: int, allowed_mime: tuple[str, ...]) -> ValidatedImage:
    """Valide les octets reçus et renvoie l'image décodée en RGB.

    - 413 si le fichier dépasse `max_bytes`
    - 422 si le fichier est vide ou illisible comme image
    - 415 si l'image est d'un format non supporté (GIF, BMP, TIFF…) ou n'est pas une image (PDF…)
    """
    size = len(data)
    if size > max_bytes:
        raise ImageValidationError(
            413, f"Fichier trop volumineux ({size / 1_048_576:.1f} Mo). Maximum : {max_bytes / 1_048_576:.0f} Mo."
        )
    if size == 0:
        raise ImageValidationError(422, "Fichier vide.")

    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
    except UnidentifiedImageError:
        # Pas une image reconnue par Pillow (PDF, texte, binaire…)
        raise ImageValidationError(
            415, "Format non supporté. Formats acceptés : JPEG, PNG, WebP."
        ) from None
    except Image.DecompressionBombError:
        raise ImageValidationError(413, "Image trop grande (nombre de pixels).") from None

    mime = PIL_FORMAT_TO_MIME.get(fmt or "")
    if mime is None or mime not in allowed_mime:
        raise ImageValidationError(
            415, f"Format {fmt or 'inconnu'} non supporté. Formats acceptés : JPEG, PNG, WebP."
        )

    try:
        probe.load()  # décodage complet : détecte les fichiers tronqués/corrompus
        rgb = probe.convert("RGB")
    except Image.DecompressionBombError:
        raise ImageValidationError(413, "Image trop grande (nombre de pixels).") from None
    except Exception:
        raise ImageValidationError(422, "Image illisible ou corrompue.") from None
    finally:
        probe.close()

    return ValidatedImage(image=rgb, mime_type=mime, size_bytes=size, width=rgb.width, height=rgb.height)


# --- Prétraitement sans PyTorch (backend ONNX) --------------------------------
# Reproduit exactement l'AutoImageProcessor de microsoft/resnet-50
# (ConvNextImageProcessor, shortest_edge=224, crop_pct=0.875) :
# redimensionnement du petit côté à 256 (bicubique), recadrage central 224×224,
# mise à l'échelle [0, 1], normalisation ImageNet, format NCHW float32.

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def to_model_input(image: Image.Image, size: int = 224, crop_pct: float = 0.875):
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
    arr = (arr - np.array(IMAGENET_MEAN, dtype=np.float32)) / np.array(IMAGENET_STD, dtype=np.float32)
    return np.ascontiguousarray(arr.transpose(2, 0, 1)[None, ...])  # (1, 3, 224, 224)
