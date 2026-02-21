import logging
import asyncio
import random
import base64
import httpx
from typing import Optional
from openai import AsyncOpenAI, OpenAIError, RateLimitError, APIConnectionError
from aiolimiter import AsyncLimiter
from config import GROK_API_KEY, GROK_BASE_URL, GROK_IMAGE_MODEL, GROK_IMAGE_PROMPT, GROK_TIMEOUT, IMAGE_RATE_LIMIT

logger = logging.getLogger(__name__)
image_limiter = AsyncLimiter(max_rate=IMAGE_RATE_LIMIT, time_period=60)


class ImageService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=GROK_API_KEY,
            base_url=GROK_BASE_URL,
            timeout=GROK_TIMEOUT
        )
        self.prompt_template = GROK_IMAGE_PROMPT
        self.model = GROK_IMAGE_MODEL

    def _validate_image_bytes(self, image_bytes: bytes) -> bool:
        """Rasmni yaroqliligini tekshirish (JPEG/PNG/WebP magic bytes)."""
        if not image_bytes or len(image_bytes) < 100:
            logger.warning(f"Image too small: {len(image_bytes) if image_bytes else 0} bytes")
            return False
        if image_bytes[:2] == b'\xff\xd8':  # JPEG
            return True
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':  # PNG
            return True
        if image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':  # WebP
            return True
        logger.warning(f"Invalid image format. First 20 bytes: {image_bytes[:20]}")
        return False

    async def generate_image(self, post_content: str) -> Optional[bytes]:
        prompt = self.prompt_template.format(post_content=post_content)

        logger.info(f"🎨 Image Generation Started | Model: {self.model}")

        if not GROK_API_KEY or GROK_API_KEY == "YOUR_GROK_API_KEY_HERE":
            logger.warning("GROK_API_KEY not configured, skipping image generation")
            return None

        max_attempts = 3
        base_delay = 2.0
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🔄 Image attempt {attempt}/{max_attempts}")

                async with image_limiter:
                    response = await self.client.images.generate(
                        model=self.model,
                        prompt=prompt
                    )

                image_data = response.data[0]

                if hasattr(image_data, 'b64_json') and image_data.b64_json:
                    image_bytes = base64.b64decode(image_data.b64_json)
                    if not self._validate_image_bytes(image_bytes):
                        raise ValueError("Decoded base64 is not a valid image")
                    logger.info(f"✅ Image decoded ({len(image_bytes)} bytes)")
                    return image_bytes

                elif hasattr(image_data, 'url') and image_data.url:
                    image_url = image_data.url
                    async with httpx.AsyncClient() as client:
                        img_response = await client.get(image_url, timeout=30.0)
                        img_response.raise_for_status()
                        content_type = img_response.headers.get('content-type', '')
                        if not content_type.startswith('image/'):
                            raise ValueError(f"Expected image content-type, got: {content_type}")
                        image_bytes = img_response.content

                    if not self._validate_image_bytes(image_bytes):
                        raise ValueError(f"Downloaded data is not a valid image ({len(image_bytes)} bytes)")
                    logger.info(f"✅ Image downloaded ({len(image_bytes)} bytes)")
                    return image_bytes
                else:
                    raise ValueError("No image data (b64_json or url) in response")

            except RateLimitError as e:
                last_error = e
                logger.warning(f"Rate limit: attempt {attempt}/{max_attempts}: {e}")
            except (APIConnectionError, OpenAIError) as e:
                last_error = e
                logger.warning(f"Transient image API error: attempt {attempt}/{max_attempts}: {e}")
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(f"Image download error: attempt {attempt}/{max_attempts}: {e}")
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected image generation error attempt {attempt}: {e}", exc_info=True)

            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, 0.25 * delay)
                await asyncio.sleep(delay + jitter)

        logger.error(f"All image generation attempts failed: {last_error}")
        return None


image_service = ImageService()
