import json
import os
import unittest
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

from fastapi import HTTPException

from app import GenerateRequest, generate, generate_notes, make_result, word_count


class _FakeResponse(BytesIO):
    def __init__(self, body: dict[str, object]) -> None:
        super().__init__(json.dumps(body).encode("utf-8"))


class StudyNotesTests(unittest.TestCase):
    @patch("app.generate_notes")
    def test_user_defined_paragraph_is_sent_for_generation(self, mock_generate: object) -> None:
        paragraph = "A user can enter any study paragraph of their choice."
        mock_generate.return_value = {"summary": "A generated summary."}

        result = generate(GenerateRequest(text=f"  {paragraph}  "))

        mock_generate.assert_called_once_with(paragraph)
        self.assertEqual(result, {"summary": "A generated summary."})

    def test_missing_api_key_returns_actionable_error(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(HTTPException) as raised:
                generate_notes("A paragraph to summarize.")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("OPENAI_API_KEY", raised.exception.detail)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "invalid-test-key"}, clear=False)
    @patch(
        "app.urllib.request.urlopen",
        side_effect=HTTPError("https://api.openai.com", 401, "Unauthorized", {}, BytesIO()),
    )
    def test_rejected_api_key_returns_actionable_error(self, mock_urlopen: object) -> None:
        with self.assertRaises(HTTPException) as raised:
            generate_notes("A paragraph to summarize.")

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("OPENAI_API_KEY", raised.exception.detail)
        mock_urlopen.assert_called_once()

    def test_word_count_handles_punctuation_and_contractions(self) -> None:
        self.assertEqual(word_count("Don't stop—keep learning: 3 useful ideas!"), 7)

    def test_metrics_for_three_different_paragraphs(self) -> None:
        examples = [
            (
                "Plants use sunlight to convert water and carbon dioxide into glucose, releasing oxygen.",
                "Plants use sunlight to make glucose from water and carbon dioxide.",
                [
                    "Plants use light energy to create glucose.",
                    "Water and carbon dioxide are raw materials.",
                    "Oxygen is released.",
                ],
                13,
                11,
                15.4,
            ),
            (
                "The printing press made books cheaper and faster to produce, spreading literacy and new ideas throughout Europe.",
                "The printing press lowered book costs and helped ideas and literacy spread.",
                [
                    "Movable type made book production faster.",
                    "Books became cheaper and more available.",
                    "Literacy and ideas spread more widely.",
                ],
                17,
                12,
                29.4,
            ),
            (
                "Burning fossil fuels increases greenhouse gases, trapping more heat and contributing to rising temperatures and changing weather.",
                "Fossil fuel emissions trap heat, driving global warming and weather changes.",
                [
                    "Fossil fuels add greenhouse gases.",
                    "More heat is trapped in the atmosphere.",
                    "Temperatures and weather patterns are affected.",
                ],
                17,
                11,
                35.3,
            ),
        ]

        for source, summary, key_points, source_count, summary_count, reduction in examples:
            with self.subTest(source=source):
                result = make_result(source, summary, key_points)
                self.assertEqual(result["key_points"], key_points)
                self.assertEqual(result["original_word_count"], source_count)
                self.assertEqual(result["summary_word_count"], summary_count)
                self.assertEqual(result["reduction_percentage"], reduction)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
    @patch("app.urllib.request.urlopen")
    def test_generate_notes_parses_model_response(self, mock_urlopen: object) -> None:
        mock_urlopen.return_value = _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Plants convert light into stored chemical energy.",
                                    "key_points": [
                                        "Chlorophyll absorbs sunlight.",
                                        "The Calvin cycle produces glucose.",
                                        "Photosynthesis releases oxygen.",
                                    ],
                                }
                            )
                        }
                    }
                ]
            }
        )

        result = generate_notes("Plants use sunlight to make food.")

        self.assertEqual(result["summary"], "Plants convert light into stored chemical energy.")
        self.assertEqual(len(result["key_points"]), 3)
        self.assertEqual(result["original_word_count"], 6)
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["messages"][1]["content"], "Plants use sunlight to make food.")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")


if __name__ == "__main__":
    unittest.main()
