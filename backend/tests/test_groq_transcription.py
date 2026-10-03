from app.features.footage_analysis.transcription import _parse_groq_transcript


def test_groq_timestamped_segments_keep_source_clock_and_words() -> None:
    results = _parse_groq_transcript(
        {
            "segments": [{"start": 1.25, "end": 3.5, "text": " A useful hook. "}],
            "words": [
                {"start": 1.25, "end": 1.6, "word": "A"},
                {"start": 1.61, "end": 2.1, "word": "useful"},
                {"start": 3.6, "end": 4.0, "word": "outside"},
            ],
        }
    )

    assert results[0].source_start_ms == 1_250
    assert results[0].source_end_ms == 3_500
    assert results[0].word_timings == [
        {"word": "A", "source_start_ms": 1_250, "source_end_ms": 1_600},
        {"word": "useful", "source_start_ms": 1_610, "source_end_ms": 2_100},
    ]
