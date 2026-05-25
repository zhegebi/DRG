import json

from loguru import logger
from openai import AsyncOpenAI

from server.config import API_KEY

try:
    client = AsyncOpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    logger.exception(f"Error initializing DeepSeek API client: {e}")
    raise Exception("Failed to initialize DeepSeek API client")


async def generate_summary(document: str, default: str) -> str:
    try:
        system_prompt = """
        请为用户输入的文档提供一个摘要, 10个字左右.
        注意: 请概括文档内容，而非只是摘取标题。e.g. "DRG 测试用例: {主要诊断}".
        格式为json对象:
        {
        "summary": "摘要内容"
        }
        """
        response = await client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": document},
            ],
            temperature=1.0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content is None:
            return default
        summary = json.loads(content)["summary"]
        return summary
    except Exception as e:
        logger.warning(f"cannot generate summary, error: {e}")
        return default
