from openai import OpenAI
from loguru import logger
from pydantic import BaseModel
from typing import Literal, List, Tuple, Union, Optional
from enum import Enum
import uuid

from .models import MedicalRecord, Complication, DrgResult, DrgTestCase, NAME_TO_CODE, DIAG_TO_MDC, MDC_ADRG_DRG, PROCEDURE_TO_ADRG, MCC_AND_CC
from ...config import API_KEY


# init the constant variables
try:   
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    logger.error(f"Error initializing DeepSeek API client: {e}")
    raise RuntimeError("Failed to initialize DeepSeek API client")

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

class TaskStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"

class Task(BaseModel):
    id: uuid.UUID
    name: str
    result: Optional[Union[DrgResult, DrgTestCase]] = None
    status: TaskStatus = TaskStatus.RUNNING
    should_generate_test: bool = False
    err_msg: Optional[str] = None

    # step 1: use DeepSeek API to extract medical record information
    def _extract_medical_record_info(self,medical_record_text: str) -> MedicalRecord:
        logger.info(f"extracting medical record info from text, task_id: {self.id}")
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
            logger.error(f"Error calling DeepSeek API on extract medical record info: {e}")
            raise RuntimeError(f"Error calling DeepSeek API on extract medical record info: {e}")
        # 2. parse response
        try:
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from DeepSeek API on extract medical record info")
            medical_record = MedicalRecord.model_validate_json(content)
            return medical_record
        except Exception as e:
            logger.error(f"Wrong medical record info format: {e}")
            raise RuntimeError(f"Wrong medical record info format: {e}")

    # step 2: get MDC code
    def _get_mdc_code(self, medical_record_text:str, medical_record: MedicalRecord) -> str:
        logger.info(f"getting MDC code from medical record, task_id: {self.id}")
        # 1. get primary diagnosis code
        primary_diagnosis_code = medical_record.primary_diagnosis.code
        if primary_diagnosis_code is None:
            primary_diagnosis_code = NAME_TO_CODE.diagnosis.get(medical_record.primary_diagnosis.name, None)
        if primary_diagnosis_code is None:
            logger.error(f"unknown diagnosis {medical_record.primary_diagnosis.name}")
            raise ValueError(f"unknown diagnosis {medical_record.primary_diagnosis.name}")
        # 2. get MDC code
        mdc_code_list = DIAG_TO_MDC.data.get(primary_diagnosis_code, None)
        if mdc_code_list is None or len(mdc_code_list) == 0:
            logger.error(f"cannot find MDC code for diagnosis {medical_record.primary_diagnosis.name}")
            raise RuntimeError(f"cannot find MDC code for diagnosis {medical_record.primary_diagnosis.name}")
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
                raise RuntimeError(f"Error getting MDC code: {e}")

    # step 3: get ADRG code
    def _get_adrg_code(self, medical_record: MedicalRecord, mdc_code: str) -> str:
        logger.info(f"getting ADRG code from medical record, task_id: {self.id}")
        # 1.get primary procedure code
        primary_procedure_code = medical_record.primary_procedure.code
        if primary_procedure_code is None:
            primary_procedure_code = NAME_TO_CODE.procedure.get(medical_record.primary_procedure.name, None)
        if primary_procedure_code is None:
            logger.error(f"unknown procedure {medical_record.primary_procedure.name}")
            raise ValueError(f"unknown procedure {medical_record.primary_procedure.name}")
        # 2. get ADRG code
        adrg_code_list = PROCEDURE_TO_ADRG.data.get(primary_procedure_code, None)
        if adrg_code_list is None or len(adrg_code_list) == 0:
            logger.error(f"cannot find ADRG code for procedure {primary_procedure_code}")
            raise RuntimeError(f"cannot find ADRG code for procedure {primary_procedure_code}")
        for result in adrg_code_list:
            if result.mdc_code == mdc_code:
                return result.adrg_code
        logger.error(f"cannot find ADRG code for MDC {mdc_code} and procedure {primary_procedure_code}")
        raise RuntimeError(f"cannot find ADRG code for MDC {mdc_code} and procedure {primary_procedure_code}")

    # step 4: get MCC and CC level
    def _get_mcc_cc_level(
        self,
        medical_record: MedicalRecord
    ) -> Literal[Complication.CC, Complication.MCC, Complication.NO]:
        logger.info(f"getting MCC and CC level from medical record, task_id: {self.id}")
        # 1. get primary diagnosis code
        primary_diagnosis_code = medical_record.primary_diagnosis.code
        if primary_diagnosis_code is None:
            primary_diagnosis_code = NAME_TO_CODE.diagnosis.get(medical_record.primary_diagnosis.name, None)
        if primary_diagnosis_code is None:
            logger.error(f"unknown diagnosis {medical_record.primary_diagnosis.name}")
            raise ValueError(f"unknown diagnosis {medical_record.primary_diagnosis.name}")
        # 2. get secondary diagnosis code list
        secondary_diagnosis_list = medical_record.secondary_diagnosis_list
        secondary_diagnosis_code_list: List[str] = []
        for diagnosis in secondary_diagnosis_list:
            diagnosis_code = diagnosis.code
            if diagnosis_code is None:
                diagnosis_code = NAME_TO_CODE.diagnosis.get(diagnosis.name, None)
            if diagnosis_code is None:
                logger.warning(f"unknown diagnosis {diagnosis.name} on secondary diagnosis list, skip")
            else:
                secondary_diagnosis_code_list.append(diagnosis_code)
        if len(secondary_diagnosis_code_list) == 0:
            return Complication.NO
        # 3. judge MCC and CC
        exclusion_tables = MCC_AND_CC.exclusion_tables
        mcc_list = MCC_AND_CC.mcc
        cc_list = MCC_AND_CC.cc
        for code in secondary_diagnosis_code_list:
            for mcc_diag in mcc_list:
                if mcc_diag.code == code:
                    exclusion_table_name = mcc_diag.exclusion_table
                    exclusion_table = exclusion_tables.get(exclusion_table_name, None)
                    if exclusion_table is None or primary_diagnosis_code not in exclusion_table:
                        return Complication.MCC
                    break
            for cc_diag in cc_list:
                if cc_diag.code == code:
                    exclusion_table_name = cc_diag.exclusion_table
                    exclusion_table = exclusion_tables.get(exclusion_table_name, None)
                    if exclusion_table is None or primary_diagnosis_code not in exclusion_table:
                        return Complication.CC
                    break
        return Complication.NO

    # step 5: get DRG code and name
    def _get_drg_code_and_name(
        self,
        adrg_code: str, 
        mcc_cc_level: Literal[Complication.CC, Complication.MCC, Complication.NO]
    ) -> Tuple[str, str]:
        """
        return (drg_code, drg_name)
        """
        logger.info(f"getting DRG code from medical record, task_id: {self.id}")
        # 1. get DRG code list
        drg_list = MDC_ADRG_DRG.drg.get(adrg_code, None)
        if drg_list is None:
            logger.error(f"cannot find DRG code list for ADRG {adrg_code}")
            raise RuntimeError(f"cannot find DRG code list for ADRG {adrg_code}")
        # 2. select DRG code
        for drg in drg_list:
            if drg.type == Complication.ANY:
                return (drg.code, drg.name)
            if drg.type == Complication.CC_or_MCC and mcc_cc_level != Complication.NO:
                return (drg.code, drg.name)
            if drg.type == mcc_cc_level:
                return (drg.code, drg.name)
        logger.error(f"cannot find DRG code for ADRG {adrg_code} and MCC and CC level {mcc_cc_level}")
        raise RuntimeError(f"cannot find DRG code for ADRG {adrg_code} and MCC and CC level {mcc_cc_level}")

    # step 6: final result
    def _get_final_result(
        self,
        medical_record: MedicalRecord,
        mdc_code: str,
        adrg_code: str,
        mcc_cc_level: Literal[Complication.CC, Complication.MCC, Complication.NO],
        drg_code: str,
        drg_name: str
    ) -> DrgResult:
        logger.info(f"getting final result, task_id: {self.id}")
        # 1. get MDC name
        mdc_name = MDC_ADRG_DRG.mdc.get(mdc_code, None)
        if mdc_name is None:
            logger.error(f"unknown MDC {mdc_code}")
            raise ValueError(f"unknown MDC {mdc_code}")
        # 2. get ADRG name
        adrg_name = MDC_ADRG_DRG.adrg.get(adrg_code, None)
        if adrg_name is None:
            logger.error(f"unknown ADRG {adrg_code}")
            raise ValueError(f"unknown ADRG {adrg_code}")
        # 3. get reason for the result
        lines = [
            f"主诊断 {medical_record.primary_diagnosis.name} 匹配到的MDC为 {mdc_code}（{mdc_name}）",
            f"手术 {medical_record.primary_procedure.name} 匹配到的ADRG为 {adrg_code}（{adrg_name}）",
            f"次诊断 {','.join([f'{diagnosis.name}' for diagnosis in medical_record.secondary_diagnosis_list])} 由此判定并发症等级为 {mcc_cc_level.value}",
            f"根据并发症等级 {mcc_cc_level.value} 选择DRG为 {drg_code}（{drg_name}）"
        ]
        return DrgResult(
            mdc=mdc_code,
            adrg=adrg_code,
            drg=drg_code,
            complication=mcc_cc_level,
            reason="\n".join(lines)
        )
    
    def run_task_without_test(self, medical_record_text: str):
        """
        run task without generating test case
        """

        try:
            medical_record = self._extract_medical_record_info(medical_record_text)
            mdc_code = self._get_mdc_code(medical_record_text, medical_record)
            adrg_code = self._get_adrg_code(medical_record, mdc_code)
            mcc_cc_level = self._get_mcc_cc_level(medical_record)
            drg_code, drg_name = self._get_drg_code_and_name(adrg_code, mcc_cc_level)
            final_result = self._get_final_result(
                medical_record, 
                mdc_code, adrg_code, 
                mcc_cc_level, 
                drg_code, 
                drg_name
            )
            self.result = final_result
            self.status = TaskStatus.SUCCESS
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.err_msg = str(e)
