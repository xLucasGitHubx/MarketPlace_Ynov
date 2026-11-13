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


def reject_non_object_image(
    image: Image.Image,
    *,
    min_side: int = 64,
    min_std: float = 8.0,
) -> None:
    """Heuristique basique : refuse images trop petites, quasi-uniformes ou sans structure.

    Lève ImageValidationError (422) si l'image ne ressemble pas à une photo d'objet.
    La variance est mesurée en luminance (pas sur les 3 canaux RGB empilés) pour
    bien détecter un aplats coloré du type (200, 30, 30).
    """
    width, height = image.size
    if width < min_side or height < min_side:
        raise ImageValidationError(
            422,
            f"Image trop petite ({width}×{height}). Minimum : {min_side}×{min_side} pixels.",
        )

    import numpy as np

    arr = np.asarray(image, dtype=np.float32)
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    # Sous-échantillonnage de pixels (sans redimensionner : le resize lisse le bruit)
    flat = gray.ravel()
    if flat.size > 65_536:
        idx = np.linspace(0, flat.size - 1, 65_536).astype(np.int64)
        sample = flat[idx]
    else:
        sample = flat
    std = float(sample.std())
    if std < min_std:
        raise ImageValidationError(
            422,
            "Image trop uniforme (fond uni ou quasi vide) : envoyez une photo d'objet contrastée.",
        )

    # Contours sur une miniature : aplats / flou extrême → peu de gradients
    thumb = gray
    if width > 128 or height > 128:
        thumb_img = image.convert("L").resize(
            (min(128, width), min(128, height)), resample=Image.Resampling.BILINEAR
        )
        thumb = np.asarray(thumb_img, dtype=np.float32)
    gx = float(np.abs(np.diff(thumb, axis=1)).mean())
    gy = float(np.abs(np.diff(thumb, axis=0)).mean())
    edge = gx + gy
    if edge < 1.5 and std < min_std * 1.25:
        raise ImageValidationError(
            422,
            "Image sans structure détectable : envoyez une photo nette d'un objet.",
        )


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
