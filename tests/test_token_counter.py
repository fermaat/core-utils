"""Unit tests for TokenCounter."""

from core_utils.token_counter import TokenCounter


class TestTokenCounter:
    def test_estimate_tokens_empty_string(self) -> None:
        assert TokenCounter.estimate_tokens("") == 0

    def test_estimate_tokens_single_word(self) -> None:
        assert TokenCounter.estimate_tokens("hello") >= 1

    def test_estimate_tokens_multiple_words(self) -> None:
        assert TokenCounter.estimate_tokens("hello world test example") >= 4

    def test_estimate_tokens_with_model(self) -> None:
        text = "This is a test message"
        assert TokenCounter.estimate_tokens(text, "default") > 0
        assert TokenCounter.estimate_tokens(text, "llama") > 0
        assert TokenCounter.estimate_tokens(text, "gpt") > 0

    def test_count_messages_tokens(self) -> None:
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        assert TokenCounter.count_messages_tokens(messages) > 0

    def test_will_fit_in_context(self) -> None:
        assert TokenCounter.will_fit_in_context("Hello", max_tokens=100)
        assert not TokenCounter.will_fit_in_context("word " * 1000, max_tokens=100)

    def test_truncate_to_fit(self) -> None:
        long_text = "word " * 100
        truncated = TokenCounter.truncate_to_fit(long_text, max_tokens=50)
        assert len(truncated) <= len(long_text)
        assert TokenCounter.will_fit_in_context(truncated, max_tokens=50, safety_margin=10)
