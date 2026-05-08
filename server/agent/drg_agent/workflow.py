from openai import OpenAI
from loguru import logger

from . import models
from ... import config


# step 0: initialize DeepSeek API client and prompts
try:   
    client = OpenAI(api_key=config.API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    logger.error(f"Error initializing DeepSeek API client: {e}")
    raise e

# step 1: use DeepSeek API to extract medical record information
EXTRACT_MEDICAL_RECORD_SYSTEM_PROMPT = """
你是一个专业的医疗记录信息提取助手。你的任务是从用户提供的医疗记录文本中，提取出结构化信息，并严格按照以下JSON格式输出：

{
  "primary_diagnosis": {"code": "编码", "name": "疾病名称"},
  "secondary_diagnosis_list": [{"code": "编码", "name": "疾病名称"}, ...],
  "primary_procedure": {"code": "编码", "name": "手术名称"},
  "other_procedures": [{"code": "编码", "name": "手术名称"}, ...]
}

提取规则：
1. 主诊断（primary_diagnosis）：文本中明确标记为“主要诊断”或类似含义的疾病。如果只有一条诊断，则视作主诊断。
2. 次要诊断（secondary_diagnosis_list）：文本中明确标记为“次要诊断”或类似含义的疾病，或者是“主要诊断”以外的其他诊断。
3. 主要手术（primary_procedure）：文本中明确标记为“主要手术”或最核心的手术操作。
4. 其他手术（other_procedures）：除主要手术外的其他手术或操作。
5. 每个诊断/手术对象必须包含code和name字段。如果文本中未提供编码，则code字段设为null，但name必须尽力提取（一定要使用病例中一模一样的名称）。
6. 如果某个列表没有内容，返回空列表[]。
7. 只输出JSON，不要输出任何其他文本或解释。
"""
def extract_medical_record_info(medical_record_text: str) -> models.MedicalRecord:
    try:
        # 1. 调用API
        response = client.chat.completions.create(
            model = "deepseek-v4-pro",
            messages = [
                {"role": "system", "content": EXTRACT_MEDICAL_RECORD_SYSTEM_PROMPT},
                {"role": "user", "content": f"请处理以下医疗记录文本：\n{medical_record_text}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        logger.error(f"Error calling DeepSeek API: {e}")
        raise e
        # 2. 解析响应
    try:
        content = response.choices[0].message.content
        medical_record = models.MedicalRecord.model_validate_json(content)
        return medical_record
    except Exception as e:
        logger.error(f"Error parsing JSON response: {e}")
        raise e
