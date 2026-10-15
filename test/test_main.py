"""Unit tests for pure helper functions in app.main."""

from app.main import (
    _unescape_transcript,
    _clean_speech,
    _split_transcript_turns,
    transcript_to_html,
    _safe_folder_name,
)


# ---------------------------------------------------------------------------
# _unescape_transcript
# ---------------------------------------------------------------------------

class TestUnescapeTranscript:
    def test_literal_newline_escape(self):
        assert _unescape_transcript("hello\\nworld") == "hello\nworld"

    def test_literal_tab_escape(self):
        assert _unescape_transcript("a\\tb") == "a\tb"

    def test_literal_carriage_return_normalized_to_newline(self):
        # Функция намеренно нормализует \r → \n
        assert _unescape_transcript("a\\rb") == "a\nb"

    def test_literal_crlf_normalized_to_newline(self):
        assert _unescape_transcript("a\\r\\nb") == "a\nb"

    def test_mixed_escapes(self):
        assert _unescape_transcript("a\\n\\nb") == "a\n\nb"

    def test_stars_on_own_line_removed(self):
        assert _unescape_transcript("text\n*\nmore") == "text\n\nmore"

    def test_double_stars_on_own_line_removed(self):
        assert _unescape_transcript("text\n**\nmore") == "text\n\nmore"

    def test_triple_stars_on_own_line_removed(self):
        assert _unescape_transcript("text\n***\nmore") == "text\n\nmore"

    def test_collapse_extra_newlines(self):
        assert _unescape_transcript("a\n\n\n\nb") == "a\n\nb"

    def test_no_escapes_no_change(self):
        assert _unescape_transcript("plain text") == "plain text"

    def test_empty_string(self):
        assert _unescape_transcript("") == ""


# ---------------------------------------------------------------------------
# _clean_speech
# ---------------------------------------------------------------------------

class TestCleanSpeech:
    def test_strips_whitespace(self):
        assert _clean_speech("  hello  ") == "hello"

    def test_strips_leading_trailing_stars(self):
        assert _clean_speech("**hello**") == "hello"

    def test_strips_single_stars(self):
        assert _clean_speech("*hello*") == "hello"

    def test_strips_curly_quotes(self):
        assert _clean_speech("“hello”") == "hello"

    def test_empty_string(self):
        assert _clean_speech("") == ""

    def test_only_whitespace_and_stars(self):
        assert _clean_speech("  * ** ") == ""


# ---------------------------------------------------------------------------
# _split_transcript_turns
# ---------------------------------------------------------------------------

class TestSplitTranscriptTurns:
    def test_no_speakers(self):
        result = _split_transcript_turns("Just a plain text.")
        assert result == [(None, "Just a plain text.")]

    def test_empty_text(self):
        result = _split_transcript_turns("")
        assert result == []

    def test_one_speaker(self):
        result = _split_transcript_turns("SPEAKER_00: Hello there.")
        assert result == [("SPEAKER_00", "Hello there.")]

    def test_two_speakers(self):
        text = "SPEAKER_00: Hi\nSPEAKER_01: Hello"
        result = _split_transcript_turns(text)
        assert result == [("SPEAKER_00", "Hi"), ("SPEAKER_01", "Hello")]

    def test_preamble_before_first_speaker(self):
        text = "Intro text\nSPEAKER_00: Hi"
        result = _split_transcript_turns(text)
        assert result == [(None, "Intro text"), ("SPEAKER_00", "Hi")]

    def test_speaker_with_stars(self):
        result = _split_transcript_turns("**SPEAKER_00**: Hello")
        assert result == [("SPEAKER_00", "Hello")]

    def test_speaker_lowercase(self):
        result = _split_transcript_turns("speaker_01: test")
        assert result == [("SPEAKER_01", "test")]

    def test_speaker_with_no_text(self):
        result = _split_transcript_turns("SPEAKER_00: SPEAKER_01: Hi")
        assert ("SPEAKER_00", "") in result
        assert ("SPEAKER_01", "Hi") in result


# ---------------------------------------------------------------------------
# transcript_to_html
# ---------------------------------------------------------------------------

class TestTranscriptToHtml:
    def test_basic(self):
        html = transcript_to_html("Title", "SPEAKER_00: Hello")
        assert "<h1>Title</h1>" in html
        assert "SPEAKER_00:" in html
        assert "Hello" in html

    def test_html_escaping_in_title(self):
        html = transcript_to_html("Title <script>alert(1)</script>", "text")
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_html_escaping_in_body(self):
        html = transcript_to_html("T", "SPEAKER_00: a & b < c")
        assert "a &amp; b &lt; c" in html

    def test_no_speaker(self):
        html = transcript_to_html("T", "Just text")
        assert "<p>Just text</p>" in html
        assert "<strong>" not in html

    def test_newlines_become_br(self):
        html = transcript_to_html("T", "SPEAKER_00: line1\\nline2")
        assert "<br/>" in html


# ---------------------------------------------------------------------------
# _safe_folder_name
# ---------------------------------------------------------------------------

class TestSafeFolderName:
    def test_slash_replaced(self):
        assert _safe_folder_name("foo/bar") == "foo_bar"

    def test_backslash_replaced(self):
        assert _safe_folder_name("foo\\bar") == "foo_bar"

    def test_dotdot_replaced(self):
        assert _safe_folder_name("a..b") == "a_b"

    def test_normal_name(self):
        assert _safe_folder_name("shared") == "shared"

    def test_empty_string(self):
        assert _safe_folder_name("") == ""

    def test_traversal_attempt(self):
        result = _safe_folder_name("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
