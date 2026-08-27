from django.test import SimpleTestCase

from apps.reading.chunking import (
    build_overview_sample,
    chunk_text,
    normalize_text,
)


class ReadingChunkingTests(SimpleTestCase):
    def test_normalize_text(
        self,
    ):
        text = "Hello\x00   world\r\n\r\n\r\nNext"

        normalized = normalize_text(text)

        self.assertEqual(
            normalized,
            "Hello world\n\nNext",
        )

    def test_chunk_orders_sequential(
        self,
    ):
        text = "\n\n".join(
            [
                "A" * 30,
                "B" * 30,
                "C" * 30,
            ]
        )

        chunks = chunk_text(
            text,
            target_chars=35,
            max_chars=40,
        )

        self.assertEqual(
            [chunk.order for chunk in chunks],
            list(
                range(
                    1,
                    len(chunks) + 1,
                )
            ),
        )

        self.assertTrue(all(chunk.char_count <= 40 for chunk in chunks))

    def test_empty_text(
        self,
    ):
        self.assertEqual(
            chunk_text("   \n\n   "),
            [],
        )

    def test_invalid_configuration(
        self,
    ):
        with self.assertRaises(ValueError):
            chunk_text(
                "hello",
                target_chars=200,
                max_chars=100,
            )

    def test_overview_sample_bounded(
        self,
    ):
        text = "A" * 10000

        sample = build_overview_sample(
            text,
            max_chars=900,
        )

        self.assertLessEqual(
            len(sample),
            1100,
        )

        self.assertIn(
            "START SAMPLE",
            sample,
        )

        self.assertIn(
            "MIDDLE SAMPLE",
            sample,
        )

        self.assertIn(
            "END SAMPLE",
            sample,
        )
