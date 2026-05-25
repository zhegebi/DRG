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
        你是一个文档摘要专家。请为输入的文档生成一个简洁的摘要。

        ## 摘要要求
        - 长度：15-25个字
        - 必须提取文档中的1-2个核心实体或关键事实作为摘要的主体，例如：文档中涉及的具体对象、数据、结论、操作、状态等
        - 禁止事项：
        - 不要使用文档的标题作为摘要
        - 不要使用"本文档"、"该文档"等泛化指代
        - 不要输出笼统的类别描述，要输出文档里实际出现的信息

        ## 策略：先定位、后概括
        1. 快速扫描文档，找到最有区分度的具体信息（如：具体名称、数值、事件、判断结论等）
        2. 用这些具体信息构成摘要，而不是用文档的类别或主题概括

        ## 输出格式
        返回JSON对象：
        {"summary": "摘要内容"}
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
