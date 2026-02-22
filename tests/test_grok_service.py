import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.grok_service import GrokService


@pytest.mark.asyncio
async def test_grok_generate_post_success():
    service = GrokService()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test post content"

    with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response

        result = await service.generate_post("test theme", is_premium=False)

        assert result == "Test post content"
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_grok_generate_post_fallback():
    service = GrokService()

    with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock, side_effect=Exception("API Error")):
        result = await service.generate_post("test theme", is_premium=False)

        assert "test theme" in result
        assert "📢" in result


@pytest.mark.asyncio
async def test_grok_retry_logic():
    service = GrokService()

    call_count = 0

    async def mock_api_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 4:
            raise Exception("Temporary error")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retries"
        return mock_response

    with patch.object(service.client.chat.completions, 'create', side_effect=mock_api_call):
        result = await service.generate_post("retry test", is_premium=True)

        assert result == "Success after retries"
        assert call_count == 4
