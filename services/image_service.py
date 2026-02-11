import logging
import asyncio
import random
import base64
import httpx
from typing import Optional
from openai import OpenAI, OpenAIError, RateLimitError, APIConnectionError
from config import GROK_API_KEY, GROK_BASE_URL, GROK_IMAGE_MODEL, GROK_IMAGE_PROMPT, GROK_TIMEOUT

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self):
        self.client = OpenAI(
            api_key=GROK_API_KEY,
            base_url=GROK_BASE_URL,
            timeout=GROK_TIMEOUT
        )
        self.prompt_template = GROK_IMAGE_PROMPT
        self.model = GROK_IMAGE_MODEL

    async def generate_image(self, post_content: str) -> Optional[bytes]:
        prompt = self.prompt_template.format(post_content=post_content)

        logger.info(f"🎨 Image Generation Started")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  Post content: {post_content[:100]}...")

        if not GROK_API_KEY or GROK_API_KEY == "YOUR_GROK_API_KEY_HERE":
            logger.warning("GROK_API_KEY not configured, skipping image generation")
            return None

        max_attempts = 3
        base_delay = 2.0
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🔄 Attempt {attempt}/{max_attempts} - Calling Grok Image API...")

                response = await asyncio.to_thread(
                    self.client.images.generate,
                    model=self.model,
                    prompt=prompt
                )

                image_data = response.data[0]

                if hasattr(image_data, 'b64_json') and image_data.b64_json:
                    logger.info(f"✅ Image generated successfully (base64 format)")
                    image_bytes = base64.b64decode(image_data.b64_json)
                    logger.info(f"✅ Image decoded successfully ({len(image_bytes)} bytes)")
                    return image_bytes

                elif hasattr(image_data, 'url') and image_data.url:
                    image_url = image_data.url
                    logger.info(f"✅ Image URL generated: {image_url[:80]}...")

                    async with httpx.AsyncClient() as client:
                        img_response = await client.get(image_url, timeout=30.0)
                        img_response.raise_for_status()
                        image_bytes = img_response.content

                    logger.info(f"✅ Image downloaded successfully ({len(image_bytes)} bytes)")
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

        logger.error(f"All image generation attempts failed for post: {last_error}")
        return None


image_service = ImageService()
