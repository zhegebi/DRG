from openai import OpenAI
from loguru import logger
from pydantic import BaseModel

from .models import MedicalRecord, NAME_TO_CODE, DIAG_TO_MDC, MDC_ADRG_DRG
from ...config import API_KEY


# step 0: initialize DeepSeek API client and prompts
try:   
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    logger.error(f"Error initializing DeepSeek API client: {e}")
    raise e

# step 1: use DeepSeek API to extract medical record information
EXTRACT_MEDICAL_RECORD_SYSTEM_PROMPT = """
你是一个专业的病历信息提取助手。你的任务是从用户提供的病历文本中，提取出结构化信息，并严格按照以下JSON格式输出：

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
5. 每个诊断/手术对象必须包含code和name字段。如果文本中未提供编码，则code字段设为null，但name必须尽力提取（一定要使用病历中一模一样的名称，尤其要注意那些虚词，比如'的'这类的一定要一样，另外如果是中文和字符之间的空格，需要去掉它，其他情况的空格需要一模一样保留）。
6. 如果某个列表没有内容，返回空列表[]。
7. 只输出JSON，不要输出任何其他文本或解释。
"""
def extract_medical_record_info(medical_record_text: str) -> MedicalRecord:
    # 1. call api
    try:
        response = client.chat.completions.create(
            model = "deepseek-v4-pro",
            messages = [
                {"role": "system", "content": EXTRACT_MEDICAL_RECORD_SYSTEM_PROMPT},
                {"role": "user", "content": f"请处理以下病历文本：\n{medical_record_text}"}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        logger.error(f"Error calling DeepSeek API: {e}")
        raise e
    # 2. parse response
    try:
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response from DeepSeek API")
        medical_record = MedicalRecord.model_validate_json(content)
        return medical_record
    except Exception as e:
        logger.error(f"Error parsing JSON response: {e}")
        raise e

# step 2: get MDC code
GET_MDC_SYSTEM_PROMPT = f"""
你是一个专业的DRG分组专家。你的任务是根据病人的完整病历文本，从多个可能的MDC（主要诊断大类）候选中选择最合理的一个。

MDC代码及其名称定义如下：
{chr(10).join([f"- {code}: {name}" for code, name in MDC_ADRG_DRG.mdc.items()])}

规则：
1. 你会收到一个病例文本和一组候选MDC代码列表。
2. 请分析病例中的主要诊断、次要诊断、手术操作、临床表现等信息，判断最匹配的MDC。
3. **输出格式必须为JSON**，结构如下：
   {{"selected_mdc": "MDC代码"}}
   只输出这个JSON对象，不要有任何额外文字。
4. 如果病例信息不足以明确区分，选择最接近的候选。
"""
def get_mdc(medical_record_text:str, medical_record: MedicalRecord) -> str:
    # get primary diagnosis code
    primary_diagnosis_code = medical_record.primary_diagnosis.code
    if primary_diagnosis_code is None:
        primary_diagnosis_code = NAME_TO_CODE.diagnosis.get(medical_record.primary_diagnosis.name, None)
    if primary_diagnosis_code is None:
        logger.error(f"unknown diagnosis {medical_record.primary_diagnosis.name}")
        raise ValueError(f"unknown diagnosis {medical_record.primary_diagnosis.name}")
    # get MDC code
    mdc_code_list = DIAG_TO_MDC.data.get(primary_diagnosis_code, None)
    if mdc_code_list is None or len(mdc_code_list) == 0:
        logger.error(f"cannot find MDC code for diagnosis {medical_record.primary_diagnosis.name}")
        raise ValueError(f"cannot find MDC code for diagnosis {medical_record.primary_diagnosis.name}")
    if len(mdc_code_list) == 1:
        return mdc_code_list[0]
    else:
        try:
            user_prompt = f"""
            病历文本：
            {medical_record_text}

            可能的MDC候选（请从以下列表中选择）：
            {", ".join([f"{code}({MDC_ADRG_DRG.mdc.get(code, '未知')})" for code in mdc_code_list])}

            请输出如下格式的JSON：
            {{"selected_mdc": "MDC代码"}}
            """
            class MdcResponse(BaseModel):
                selected_mdc: str
            response = client.chat.completions.create(
                model = "deepseek-v4-pro",
                messages = [
                    {"role": "system", "content": GET_MDC_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if content is None:
                logger.warning(f"cannot choose MDC code from {mdc_code_list}, use default {mdc_code_list[0]}")
                return mdc_code_list[0]
            data = MdcResponse.model_validate_json(content)
            chosen = data.selected_mdc.strip()
            if chosen in mdc_code_list:
                return chosen
            else:
                logger.warning(f"cannot choose MDC code from {mdc_code_list}, use default {mdc_code_list[0]}")
                return mdc_code_list[0]
        except Exception as e:
            logger.error(f"Error getting MDC code: {e}")
            raise e
