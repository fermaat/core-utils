"""
Token counting utilities for managing context windows.

Provides utilities to estimate token counts for different models
based on word count and per-model multipliers.
"""


class TokenCounter:
    """
    Utility for estimating token counts.

    Uses word-count heuristics with per-model multipliers.
    These are approximations — for exact counts use the provider's native tokenizer.
    """

    TOKENS_PER_WORD = {
        "llama": 1.3,
        "mistral": 1.3,
        "neural": 1.2,
        "gpt": 1.3,
        "claude": 1.4,
        "default": 1.3,
    }

    @staticmethod
    def estimate_tokens(text: str, model: str = "default") -> int:
        """Estimate the number of tokens for a given text."""
        if not text:
            return 0

        model_lower = model.lower()
        multiplier = TokenCounter.TOKENS_PER_WORD.get("default", 1.3)
        for key, value in TokenCounter.TOKENS_PER_WORD.items():
            if key in model_lower:
                multiplier = value
                break

        word_count = len(text.split())
        return max(int(word_count * multiplier), 1)

    @staticmethod
    def count_messages_tokens(messages: list[dict[str, str]], model: str = "default") -> int:
        """Estimate total tokens for a list of messages, including per-message overhead."""
        total_tokens = 0
        for message in messages:
            content = message.get("content", "")
            total_tokens += TokenCounter.estimate_tokens(content, model)
            total_tokens += 4  # overhead per message (role, separators)
        return total_tokens

    @staticmethod
    def will_fit_in_context(
        text: str, max_tokens: int, model: str = "default", safety_margin: int = 0
    ) -> bool:
        """Return True if the estimated token count fits within max_tokens."""
        return TokenCounter.estimate_tokens(text, model) + safety_margin <= max_tokens

    @staticmethod
    def truncate_to_fit(
        text: str,
        max_tokens: int,
        model: str = "default",
        safety_margin: int = 100,
    ) -> str:
        """Truncate text so its estimated token count fits within max_tokens."""
        if TokenCounter.will_fit_in_context(text, max_tokens, model, safety_margin):
            return text

        available_tokens = max_tokens - safety_margin
        multiplier = TokenCounter.TOKENS_PER_WORD.get("default", 1.3)
        for key, value in TokenCounter.TOKENS_PER_WORD.items():
            if key in model.lower():
                multiplier = value
                break

        max_words = max(int(available_tokens / multiplier), 1)
        return " ".join(text.split()[:max_words])


__all__ = ["TokenCounter"]
