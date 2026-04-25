from unittest.mock import MagicMock, patch
import query_rewriter


def test_no_history_returns_original_message():
    result = query_rewriter.rewrite_query([], "What is WPI?")
    assert result == "What is WPI?"


def test_no_history_makes_no_api_call():
    with patch.object(query_rewriter, "anthropic") as mock_anthropic:
        query_rewriter.rewrite_query([], "Hello")
        mock_anthropic.Anthropic.assert_not_called()


def test_with_history_calls_api_and_returns_string():
    with patch.object(query_rewriter, "anthropic") as mock_anthropic:
        mock_response = MagicMock()
        mock_response.content[0].text = "What are WPI's graduate tuition fees?"
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        history = [{"role": "user", "content": "Tell me about WPI graduate programs"}]
        result = query_rewriter.rewrite_query(history, "What about fees?")

        assert isinstance(result, str)
        assert len(result) > 0


def test_rewriter_trims_history_to_last_six_messages():
    with patch.object(query_rewriter, "anthropic") as mock_anthropic:
        mock_response = MagicMock()
        mock_response.content[0].text = "Rewritten question"
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        query_rewriter.rewrite_query(history, "follow up")

        call_args = mock_anthropic.Anthropic.return_value.messages.create.call_args
        prompt_content = call_args.kwargs["messages"][0]["content"]
        # Only last 6 messages should appear in the prompt
        assert "msg 9" in prompt_content
        assert "msg 3" not in prompt_content
