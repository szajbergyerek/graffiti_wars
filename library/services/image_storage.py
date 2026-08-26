import hashlib
import os

from werkzeug.datastructures import FileStorage as UploadedFile
from werkzeug.utils import secure_filename

from library.extensions import db
from library.models.image import Image

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


class ImageStorage:
    """
    Saves an uploaded image to disk under a hash of its own content, and
    records it as an `Image` row so the rest of the app links to it by id
    instead of a raw path. Uploading the same file twice reuses the same
    row and file instead of storing a duplicate.
    """

    def __init__(self, images_root: str) -> None:
        self.images_root = images_root

    def save(self, file: UploadedFile, category: str, uploaded_by_id: int = None) -> Image:
        """
        Persist an uploaded file under `images_root/category/<hash>.<ext>`.

        param file: The uploaded file object from a Flask request.
        param category: Which image category this belongs to ("avatars", "banners", or "tags").
        param uploaded_by_id: The id of the user who uploaded it, for provenance.

        :return: The `Image` row for this file (newly created, or the existing one if identical content was seen before).
        """
        extension = secure_filename(file.filename).rsplit(".", 1)[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {extension}")

        data = file.read()
        file_hash = hashlib.sha256(data).hexdigest()
        relative_path = f"{category}/{file_hash}.{extension}"

        existing = Image.query.filter_by(relative_path=relative_path).first()
        if existing is not None:
            return existing

        target_dir = os.path.join(self.images_root, category)
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
