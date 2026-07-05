import hashlib
import math
import re


LOCAL_HASHING_EMBEDDING_MODEL = "local-hashing-v1"
LOCAL_HASHING_EMBEDDING_DIMENSIONS = 64
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


class LocalHashingEmbeddingProvider:
    model_name = LOCAL_HASHING_EMBEDDING_MODEL
    dimensions = LOCAL_HASHING_EMBEDDING_DIMENSIONS

    def embed(self, text):
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall((text or "").lower())

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector

        return [round(value / magnitude, 8) for value in vector]


def cosine_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(float(a) * float(b) for a, b in zip(left, right))
