import imagehash
from PIL import Image


class TagVerifier:
    """
    Estimates how likely a submitted tag photo shows the same piece as a
    band's registered reference image, using perceptual hashing and color
    histogram comparison.

    This is a lightweight, fully offline stand-in for a production
    embedding model (e.g. CLIP): swap the body of `score()` for a real
    model call later without touching any caller.
    """

    APPROVE_THRESHOLD = 0.6
    HASH_SIZE = 16

    def score(self, reference_path: str, submitted_path: str) -> float:
        """
        Compute a similarity score between a band's reference tag and a submitted photo.

        param reference_path: Filesystem path to the band's registered reference tag image.
        param submitted_path: Filesystem path to the newly submitted photo.

        :return: A similarity score between 0.0 (no match) and 1.0 (identical).
        """
        reference_image = Image.open(reference_path).convert("RGB")
        submitted_image = Image.open(submitted_path).convert("RGB")

        hash_similarity = self._hash_similarity(reference_image, submitted_image)
        color_similarity = self._histogram_similarity(reference_image, submitted_image)
        return float(max(0.0, min(1.0, 0.6 * hash_similarity + 0.4 * color_similarity)))

    def decide_status(self, score: float) -> str:
        """
        Translate a similarity score into a submission status. Verification
        is fully automatic - there is no manual admin review step.

        param score: The similarity score produced by `score()`.

        :return: "approved" or "rejected".
        """
        return "approved" if score >= self.APPROVE_THRESHOLD else "rejected"

    def _hash_similarity(self, reference_image: Image.Image, submitted_image: Image.Image) -> float:
        reference_hash = imagehash.phash(reference_image, hash_size=self.HASH_SIZE)
        submitted_hash = imagehash.phash(submitted_image, hash_size=self.HASH_SIZE)
        max_distance = self.HASH_SIZE * self.HASH_SIZE
        distance = reference_hash - submitted_hash
        return 1.0 - (distance / max_distance)

    def _histogram_similarity(self, reference_image: Image.Image, submitted_image: Image.Image) -> float:
        reference_histogram = reference_image.resize((128, 128)).histogram()
        submitted_histogram = submitted_image.resize((128, 128)).histogram()

        dot_product = sum(a * b for a, b in zip(reference_histogram, submitted_histogram))
        reference_magnitude = sum(a * a for a in reference_histogram) ** 0.5
        submitted_magnitude = sum(b * b for b in submitted_histogram) ** 0.5

        if reference_magnitude == 0 or submitted_magnitude == 0:
            return 0.0
        return dot_product / (reference_magnitude * submitted_magnitude)
