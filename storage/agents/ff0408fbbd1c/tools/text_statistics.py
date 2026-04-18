"""Compute text statistics: word count, sentence count, character count, top keywords."""

import re
from collections import Counter
from typing import Dict, List, Set


# Basic English stop words for keyword filtering
STOP_WORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "was", "are", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "dare", "ought", "used", "not", "no", "nor", "so", "yet", "both",
    "each", "few", "more", "most", "other", "some", "such", "than",
    "too", "very", "just", "because", "if", "when", "where", "how",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
    "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "its", "itself", "they",
    "them", "their", "theirs", "themselves", "am", "were", "about",
    "above", "after", "again", "against", "all", "any", "between",
    "into", "through", "during", "before", "below", "down", "up",
    "out", "off", "over", "under", "further", "then", "once", "here",
    "there", "why", "also", "only", "own", "same", "don", "t", "s",
}


def text_statistics(input_data: dict) -> dict:
    """Compute text statistics: word count, sentence count, character count, top keywords.

    Parameters:
        text (str): Text to analyze
        top_n (int, optional): Number of top keywords, default 10
        stop_words (list, optional): Words to exclude from keyword analysis

    Returns:
        dict with keys: word_count, sentence_count, char_count, paragraph_count,
        avg_word_length, avg_sentence_length, top_keywords, and optionally error.
    """
    text = input_data.get("text")
    if not isinstance(text, str):
        return {"error": "Missing or invalid required parameter: text"}

    top_n = input_data.get("top_n", 10)
    custom_stop_words = input_data.get("stop_words")

    if not isinstance(top_n, int) or top_n <= 0:
        return {"error": "Parameter 'top_n' must be a positive integer"}

    # Build the stop words set
    excluded: Set[str] = set(STOP_WORDS)
    if custom_stop_words and isinstance(custom_stop_words, list):
        excluded.update(w.lower() for w in custom_stop_words if isinstance(w, str))

    # Character count
    char_count = len(text)

    # Words: split on whitespace and filter out empty / pure-punctuation tokens
    word_pattern = re.compile(r"[a-zA-Z0-9''\-]+")
    words: List[str] = word_pattern.findall(text)
    word_count = len(words)

    # Sentences: split on sentence-ending punctuation followed by space or end-of-string
    sentences = re.split(r"[.!?]+(?:\s|$)", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences) if sentences else (1 if text.strip() else 0)

    # Paragraphs: separated by one or more blank lines
    paragraphs = re.split(r"\n\s*\n", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    paragraph_count = len(paragraphs) if paragraphs else (1 if text.strip() else 0)

    # Average word length
    if word_count > 0:
        total_word_chars = sum(len(w) for w in words)
        avg_word_length = round(total_word_chars / word_count, 2)
    else:
        avg_word_length = 0.0

    # Average sentence length (in words)
    if sentence_count > 0:
        avg_sentence_length = round(word_count / sentence_count, 2)
    else:
        avg_sentence_length = 0.0

    # Top keywords: lowercase, exclude stop words and single characters
    keyword_candidates = [
        w.lower() for w in words
        if w.lower() not in excluded and len(w) > 1
    ]
    keyword_counts = Counter(keyword_candidates)
    top_keywords: List[Dict[str, object]] = [
        {"word": word, "count": count}
        for word, count in keyword_counts.most_common(top_n)
    ]

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "char_count": char_count,
        "paragraph_count": paragraph_count,
        "avg_word_length": avg_word_length,
        "avg_sentence_length": avg_sentence_length,
        "top_keywords": top_keywords,
    }
