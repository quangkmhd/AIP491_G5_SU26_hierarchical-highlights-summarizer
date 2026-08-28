from service.multiscale_text_tiling import MultiscaleTextTilingService


MULTI_TOPIC_UTTERANCES = [
    "du an alpha backend api database",
    "alpha backend database endpoint",
    "alpha api service database",
    "backend alpha release api",
    "marketing campaign customer brand",
    "brand campaign social customer",
    "marketing social media brand",
    "customer campaign budget marketing",
    "server cloud deployment docker",
    "docker cloud monitoring server",
    "deployment server latency cloud",
    "monitoring docker release server",
]


def make_segmenter() -> MultiscaleTextTilingService:
    return MultiscaleTextTilingService(
        block_size=1,
        radii=[1, 2],
        alpha=0.7,
        use_stopwords=False,
        window_size=8,
        stride=2,
    )


def test_streaming_update_plus_flush_matches_batch_topic_ranges() -> None:
    expected = [(0, 3), (4, 7), (8, 11)]
    assert make_segmenter().process(MULTI_TOPIC_UTTERANCES) == expected

    streaming = make_segmenter()
    actual: list[tuple[int, int]] = []
    for utterance in MULTI_TOPIC_UTTERANCES:
        actual.extend(streaming.update(utterance))
    actual.extend(streaming.flush())

    assert actual == expected


def test_streaming_does_not_close_tail_before_explicit_flush() -> None:
    streaming = make_segmenter()

    events_before_window = [
        streaming.update(utterance) for utterance in MULTI_TOPIC_UTTERANCES[:7]
    ]

    assert events_before_window == [[], [], [], [], [], [], []]
    assert streaming.flush() == [(0, 3), (4, 6)]
