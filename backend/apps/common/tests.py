from django.test import SimpleTestCase

from apps.common.text import repair_mojibake


class TextEncodingTests(SimpleTestCase):
    def test_repair_mojibake_fixes_utf8_text_decoded_as_cp1251(self):
        original = "что написано про опыт работы"
        broken = original.encode("utf-8").decode("cp1251")

        self.assertEqual(repair_mojibake(broken), original)

    def test_repair_mojibake_keeps_normal_text_unchanged(self):
        text = "нормальный русский текст"

        self.assertEqual(repair_mojibake(text), text)
