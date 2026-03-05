import logging
import asyncio
import random
import hashlib
import re
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from openai import AsyncOpenAI, OpenAIError, RateLimitError, APIConnectionError
from config import (
    GROK_API_KEY, GROK_BASE_URL, GROK_TIMEOUT,
    GROK_MODEL_PREMIUM, GROK_MODEL_FREE,
    GROK_PROMPT_FREE, GROK_PROMPT_PREMIUM,
    GROK_MAX_TOKENS_FREE, GROK_MAX_TOKENS_PREMIUM,
    TIMEZONE
)
from aiolimiter import AsyncLimiter
from services.circuit_breaker import CircuitBreaker
from config import GROK_RATE_LIMIT
from utils.database import db

logger = logging.getLogger(__name__)
grok_limiter = AsyncLimiter(max_rate=GROK_RATE_LIMIT, time_period=60)

CURRENCY_KEYWORDS = {"dollar", "valyuta", "kurs", "rubl", "yevro", "evro", "usd", "eur", "rub", "so'm"}
CBU_API_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"


async def fetch_exchange_rates() -> Optional[str]:
    """Markaziy bankdan (cbu.uz) bugungi valyuta kurslarini olish."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(CBU_API_URL) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                rates = {}
                for item in data:
                    if item.get("Ccy") in ("USD", "EUR", "RUB", "GBP", "CNY"):
                        rates[item["Ccy"]] = item["Rate"]
                if not rates:
                    return None
                date_str = data[0].get("Date", "")
                lines = [f"O'zbekiston Markaziy banki kurslari ({date_str}):"]
                for ccy, rate in rates.items():
                    lines.append(f"  1 {ccy} = {rate} so'm")
                return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Failed to fetch exchange rates: {e}")
        return None


def _is_currency_topic(theme: str) -> bool:
    """Mavzu valyuta kurslariga oidmi tekshirish."""
    theme_lower = theme.lower()
    return any(kw in theme_lower for kw in CURRENCY_KEYWORDS)


class GrokService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=GROK_API_KEY,
            base_url=GROK_BASE_URL,
            timeout=GROK_TIMEOUT
        )
        self.circuit = CircuitBreaker(
            name="grok_api",
            failure_threshold=5,
            recovery_timeout=60.0
        )

    async def generate_post(self, theme: str, is_premium: bool = False) -> str:
        now = datetime.now(ZoneInfo(TIMEZONE))
        today_str = now.strftime("%d-%B %Y, %A")

        if is_premium:
            model = GROK_MODEL_PREMIUM
            prompt = GROK_PROMPT_PREMIUM.format(user_words=theme, today=today_str)
            max_tokens = GROK_MAX_TOKENS_PREMIUM
        else:
            model = GROK_MODEL_FREE
            prompt = GROK_PROMPT_FREE.format(user_words=theme, today=today_str)
            max_tokens = GROK_MAX_TOKENS_FREE

        # Valyuta mavzusi bo'lsa — real kurslarni promptga kiritish
        if _is_currency_topic(theme):
            rates_text = await fetch_exchange_rates()
            if rates_text:
                prompt += f"\n\nBUGUNGI REAL VALYUTA KURSLARI (Markaziy bank ma'lumoti):\n{rates_text}\nSHU ANIQ RAQAMLARNI ISHLAT!"

        logger.info(f"🤖 Grok | Model: {model} | Theme: '{theme}' | Premium: {is_premium}")

        if not GROK_API_KEY or GROK_API_KEY == "YOUR_GROK_API_KEY_HERE":
            logger.warning("GROK_API_KEY not configured, using fallback message")
            return f"📢 {theme}\n\nQiziqarli yangiliklar tez orada!"

        # Circuit breaker tekshiruvi
        if not self.circuit.can_execute():
            logger.warning(f"Circuit OPEN, fallback: theme='{theme}'")
            return f"📢 {theme}\n\nQiziqarli yangiliklar tez orada!"

        max_attempts = 4
        base_delay = 1.0
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                unique_id = hashlib.md5(f"{theme}{datetime.now().isoformat()}{random.randint(1, 999999)}".encode()).hexdigest()[:8]

                system_prompt = (
                    f"Sen professional Telegram kanal kontenti yaratuvchi mutaxassissan. "
                    f"BUGUNGI SANA: {today_str}. "
                    f"Yangiliklar, sport, voqealar haqida yozganda FAQAT bugungi yoki so'nggi kunlardagi real ma'lumotlarni ishlatasan. "
                    f"Eskilik ma'lumotlarni BERMA. Har doim so'ralgan formatda javob berasan. "
                    f"MUHIM: Har safar MUTLAQO YANGI va OLDINGILARDAN FARQLI kontent yarat. "
                    f"Bir xil iqtibos, fakt yoki ma'lumotni TAKRORLAMA. "
                    f"Agar iqtibos so'ralsa - har safar BOSHQA shaxsdan yoki shu shaxsning BOSHQA iqtibosini yoz. "
                    f"Xilma-xillik va originallik eng muhim! [UID:{unique_id}]"
                )

                async with grok_limiter:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=1.0,
                        max_tokens=max_tokens
                    )

                generated_text = response.choices[0].message.content.strip()
                # Telegram HTML da qo'llab-quvvatlanmaydigan teglarni tozalash
                generated_text = re.sub(r'<br\s*/?>', '\n', generated_text)
                generated_text = re.sub(r'<(?!/?(?:b|i|u|s|a|code|pre)\b)[^>]+>', '', generated_text)
                self.circuit.record_success()

                # Token usage tracking
                if hasattr(response, 'usage') and response.usage:
                    try:
                        await db.record_api_usage(
                            model=model,
                            input_tokens=response.usage.prompt_tokens or 0,
                            output_tokens=response.usage.completion_tokens or 0
                        )
                    except Exception as usage_err:
                        logger.warning(f"Failed to record API usage: {usage_err}")

                logger.info(f"✅ Post generated: {generated_text[:80]}...")
                return generated_text

            except RateLimitError as e:
                last_error = e
                self.circuit.record_failure()
                logger.warning(f"Rate limit: attempt {attempt}/{max_attempts}: {e}")
            except (APIConnectionError, OpenAIError) as e:
                last_error = e
                self.circuit.record_failure()
                logger.warning(f"Grok error: attempt {attempt}/{max_attempts}: {e}")
            except Exception as e:
                last_error = e
                self.circuit.record_failure()
                logger.error(f"Unexpected Grok error attempt {attempt}: {e}", exc_info=True)

            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, 0.25 * delay)
                await asyncio.sleep(delay + jitter)

        logger.error(f"All Grok attempts failed for theme='{theme}': {last_error}")
        return f"📢 {theme}\n\nQiziqarli yangiliklar tez orada!"


grok_service = GrokService()
