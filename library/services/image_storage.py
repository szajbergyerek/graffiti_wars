import hashlib
import io
import os

from PIL import Image as PILImage
from PIL import ImageOps, UnidentifiedImageError
from werkzeug.datastructures import FileStorage as UploadedFile

from library.extensions import db
from library.models.image import Image
from library.services.settings_service import SettingsService

settings_service = SettingsService()


class ImageStorage:
    """
    Validates, compresses, and saves an uploaded image to disk under a hash
    of its own (re-encoded) content, and records it as an `Image` row so the
    rest of the app links to it by id instead of a raw path. Uploading the
    same content twice reuses the same row and file instead of storing a
    duplicate.

    Every upload is decoded and re-encoded as JPEG - this is both how
    compression happens and how a non-image file gets rejected. Checking
    only the filename extension can't tell a genuine photo from an arbitrary
    file renamed to look like one; actually decoding it can.
    """

    def __init__(self, images_root: str) -> None:
        self.images_root = images_root

    def save(self, file: UploadedFile, category: str, uploaded_by_id: int = None, subfolder: str = None) -> Image:
        """
        Persist an uploaded file under `images_root/category/<hash>.jpg`, or
        `images_root/category/<subfolder>/<hash>.jpg` when a subfolder is given.

        param file: The uploaded file object from a Flask request.
        param category: Which image category this belongs to ("avatars", "banners", "tags", ...).
        param uploaded_by_id: The id of the user who uploaded it, for provenance.
        param subfolder: An optional extra path segment to nest this file under (e.g. a band id).

        :return: The `Image` row for this file (newly created, or the existing one if identical content was seen before).
        """
        raw_data = file.read()

        max_upload_bytes = int(settings_service.get("max_upload_size_mb") * 1024 * 1024)
        if len(raw_data) > max_upload_bytes:
            raise ValueError("File is too large.")

        try:
            decoded = PILImage.open(io.BytesIO(raw_data))
            decoded = ImageOps.exif_transpose(decoded)
            decoded = decoded.convert("RGB")
        except (UnidentifiedImageError, OSError) as error:
            raise ValueError("File is not a valid image.") from error

        max_dimension = settings_service.get_int("image_max_dimension_px")
        if max(decoded.width, decoded.height) > max_dimension:
            decoded.thumbnail((max_dimension, max_dimension), PILImage.Resampling.LANCZOS)

        quality = settings_service.get_int("image_jpeg_quality")
        buffer = io.BytesIO()
        decoded.save(buffer, format="JPEG", quality=quality, optimize=True)
        data = buffer.getvalue()

        extension = "jpg"
        file_hash = hashlib.sha256(data).hexdigest()
        category_path = f"{category}/{subfolder}" if subfolder else category
        relative_path = f"{category_path}/{file_hash}.{extension}"

        existing = Image.query.filter_by(relative_path=relative_path).first()
        if existing is not None:
            return existing

        target_dir = os.path.join(self.images_root, category_path)
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, f"{file_hash}.{extension}"), "wb") as target_file:
            target_file.write(data)

        image = Image(
            category=category,
            file_hash=file_hash,
            extension=extension,
            relative_path=relative_path,
            uploaded_by_id=uploaded_by_id,
        )
        db.session.add(image)
        db.session.flush()
        return image
