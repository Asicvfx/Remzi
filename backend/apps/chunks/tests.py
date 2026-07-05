from django.test import SimpleTestCase

from apps.chunks.services import TextChunker


class TextChunkerTests(SimpleTestCase):
    def test_split_returns_overlapping_chunks(self):
        chunker = TextChunker(max_tokens=4, overlap_tokens=1)

        chunks = chunker.split("one two three four five six seven")

        self.assertEqual(
            chunks,
            [
                "one two three four",
                "four five six seven",
            ],
        )

    def test_split_returns_empty_list_for_blank_text(self):
        chunker = TextChunker(max_tokens=4, overlap_tokens=1)

        self.assertEqual(chunker.split("   "), [])
