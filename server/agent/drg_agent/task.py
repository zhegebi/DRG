from datetime import datetime
from openai import OpenAI
from loguru import logger
from pydantic import BaseModel, Field
from typing import Literal, List, Tuple, Union, Optional
from enum import Enum
import uuid

from .models import MedicalRecord, Complication, DrgResult, DrgResultWithTestCase, DrgTestCase, NAME_TO_CODE, DIAG_TO_MDC, MDC_ADRG_DRG, PROCEDURE_TO_ADRG, MCC_AND_CC, DIAG_TO_MDC_TEST, PROCEDURE_TO_ADRG_TEST, MCC_AND_CC_TEST, NAME_TO_CODE_TEST
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

SELECT_TEST_CASE_TYPE_SYSTEM_PROMPT = """
你是一个测试用例类型分类器。根据用户的描述，判断其需要生成的 DRG 测试用例类型。

类型定义：
- normal: 正常场景测试用例。常规的、符合典型规则的诊断与手术组合，不刻意制造边缘情况或错误。
- boundary: 边界测试用例。重点测试 MCC/CC 排除表逻辑、疾病编码落在排除表中导致等级变化的场景，或者诊断/手术组合处于规则边界。
- abnormal: 异常测试用例。故意包含编码错误、信息缺失（例如缺少主诊断或主要手术）、不存在的编码组合等非法情况。

你必须只输出一个 JSON 对象，格式如下：
{"type": "normal"}
或
{"type": "boundary"}
或
{"type": "abnormal"}

不要输出任何其他文字、注释或解释。如果用户输入无法明确归类，则输出 {"type": "normal"}。
"""

GENERATE_TEST_CASE_SYSTEM_PROMPT = f"""
你是一个专业的 DRG 分组测试用例生成器。你必须根据以下规则，生成一个包含随机病历和该病历预期 DRG 入组结果的测试用例。

## 1. 可用的诊断（名称与编码）
{"\n".join([f"- {name}: {code}" for name, code in NAME_TO_CODE_TEST.diagnosis.items()])}

## 2. 可用的手术（名称与编码）
{"\n".join([f"- {name}: {code}" for name, code in NAME_TO_CODE_TEST.procedure.items()])}

## 3. MDC 映射规则（主诊断 -> MDC列表）
{"\n".join([f"{code} -> {mdc_list}" for code, mdc_list in DIAG_TO_MDC_TEST.data.items() if mdc_list])}

MDC 名称：
{"\n".join([f"{code}: {name}" for code, name in MDC_ADRG_DRG.mdc.items()])}

## 4. 手术 -> ADRG 映射规则（主要手术 + MDC -> ADRG）
{"\n".join(
    f"{proc_code} 在 MDC {entry.mdc_code} 下可映射到 ADRG {entry.adrg_code}"
    for proc_code, entries in PROCEDURE_TO_ADRG_TEST.data.items()
    for entry in entries
)}

ADRG 名称：
{"\n".join([f"{code}: {name}" for code, name in MDC_ADRG_DRG.adrg.items()])}

## 5. MCC (严重合并症) 列表及其排除表
{"\n".join(
    f"- {item.code} 排除: {', '.join(MCC_AND_CC_TEST.exclusion_tables.get(item.exclusion_table, []))}" 
    if MCC_AND_CC_TEST.exclusion_tables.get(item.exclusion_table) 
    else f"- {item.code} 无排除"
    for item in MCC_AND_CC_TEST.mcc
)}

## 6. CC (一般合并症) 列表及其排除表
{"\n".join(
    f"- {item.code} 排除: {', '.join(MCC_AND_CC_TEST.exclusion_tables.get(item.exclusion_table, []))}" 
    if MCC_AND_CC_TEST.exclusion_tables.get(item.exclusion_table) 
    else f"- {item.code} 无排除"
    for item in MCC_AND_CC_TEST.cc
)}

## 7. 并发症等级判定规则(mcc, cc, no最终取值都是小写)
- 首先检查所有次要诊断，如果某个诊断在 MCC 列表中，且主诊断不在该 MCC 的排除表中，则并发症等级 = mcc。
- 否则检查所有次要诊断，如果某个诊断在 CC 列表中，且主诊断不在该 CC 的排除表中，则并发症等级 = cc。
- 否则并发症等级 = no。

## 8. ADRG 到 DRG 的选择规则
{"\n".join(
    f"ADRG {adrg_code}: " + "; ".join(
        f"{({'any': '无条件', 'mcc': '当并发症==mcc', 'cc': '当并发症==cc', 'no': '当并发症==no', 'cc_or_mcc': '当并发症==cc或mcc'}[drg.type])} -> {drg.code}"
        for drg in drg_list
    )
    for adrg_code, drg_list in MDC_ADRG_DRG.drg.items()
)}

## 9. 输出格式要求
你必须输出一个合法的 JSON 对象，结构如下：

{{
  "medical_record_text": "完整的病例描述文本，必须是一段字符串，不是 JSON 对象；内容应包含性别、年龄(0-120)、
  主要诊断(包含"疾病名称"(必须来自上面的诊断列表),"疾病编码"(必须与名称匹配))、
  次要诊断列表(列表包含1-4个次要诊断, 可与主诊断不同，也可是其他诊断, 次要诊断包含疾病名称和疾病编码)、
  主要手术(包含"手术名称"(必须来自上面的手术列表),"手术编码","手术级别"(整数(1-4, 随机)))、
  其他手术列表(列表包含1-3个其他手术, 每个手术包含手术名称、手术编码、手术级别)。",
  "expected_result": {{
    "mdc": "mdc_code",
    "adrg": "adrg_code",
    "drg": "drg_code",
    "complication": "mcc" 或 "cc" 或 "no",
    "reason": "详细的推理过程，例如：主诊断 XXX 匹配到的MDC为...；手术 XXX 在MDC...下匹配到ADRG...；次要诊断... 判定并发症等级为...；根据并发症等级选择DRG..."
  }}
}}

重要提醒：
- 所有疾病名称和手术名称必须严格从上面提供的列表中选取。
- 主诊断必须能通过第3条规则映射到一个MDC（即在上面的诊断->MDC列表中有定义）。
- 主要手术必须在第4条规则中，针对所选MDC存在对应的ADRG。
- 预期结果必须严格按照上述 DRG 分组规则计算得出，不能随意编造。
- 输出必须是纯 JSON 格式，不要有其他解释文字。
- "medical_record_text" 字段后面是一个字符串类型，不要写成其他类型了。
"""




class TaskStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"

class Task(BaseModel):
    id: uuid.UUID
    name: str
    user_input: str
    result: Optional[Union[DrgResult, DrgResultWithTestCase]] = None
    status: TaskStatus = TaskStatus.RUNNING
    should_generate_test: bool = False
    err_msg: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    """
    workflow of infer DRG result from medical record text
    """
    # step 1: use DeepSeek API to extract medical record information
    def _extract_medical_record_info(self, medical_record_text: str) -> MedicalRecord:
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
    

    """
    workflow of generating DRG test case
    """
    # step 1: select test case type
    def _select_test_case_type(self, user_input: str) -> Literal["normal", "boundary", "abnormal"]:
        logger.info(f"selecting test case type from user input:\n{user_input} \ntask_id: {self.id}")
        try:
            class TestCaseTypeResponse(BaseModel):
                type: Literal["normal", "boundary", "abnormal"]
            user_prompt = f"用户需求: {user_input}"
            response = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=[
                    {"role": "system", "content": SELECT_TEST_CASE_TYPE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if content is None:
                logger.warning(f"cannot select test case type from user input by deepseek: {user_input}, use default normal")
                return "normal"
            test_case_type = TestCaseTypeResponse.model_validate_json(content).type
            return test_case_type
        except Exception as e:
            logger.error(f"cannot select test case type, error: {e}")
            raise RuntimeError(f"cannot select test case type, error: {e}")

    # step 2: generate test case
    def _generate_test_case(
        self, 
        test_case_type: Literal["normal", "boundary", "abnormal"]
    ) -> DrgTestCase:
        logger.info(f"generating test case, task_id: {self.id}")
        # write test case prompt
        match test_case_type:
            case "normal":
                test_case_prompt = """
                请生成一个随机但符合规则的正常场景测试用例
                （指的是常规的、符合典型规则的诊断与手术组合，不刻意制造边缘情况或错误。）
                """
            case "boundary":
                test_case_prompt = """
                请生成一个随机但符合规则的边界测试用例
                （重点在于测试 MCC/CC 排除表逻辑、疾病编码正好落在排除表中导致等级变化的场景。）
                """
            case "abnormal":
                test_case_prompt = """
                请生成一个随机但符合规则的异常场景测试用例
                （故意包含编码错误、信息缺失（例如缺少主诊断或主要手术）、不存在的编码组合等非法情况。）
                """
            case _:
                logger.warning(f"unknown test case type {test_case_type}, use default normal")
                test_case_prompt = """
                请生成一个随机但符合规则的正常场景测试用例
                （指的是常规的、符合典型规则的诊断与手术组合，不刻意制造边缘情况或错误。）
                """
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=[
                    {"role": "system", "content": GENERATE_TEST_CASE_SYSTEM_PROMPT},
                    {"role": "user", "content": test_case_prompt}
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if content is None:
                logger.error("cannot generate test case from deepseek")
                raise RuntimeError("cannot generate test case from deepseek")
            test_case = DrgTestCase.model_validate_json(content)
            return test_case
        except Exception as e:
            logger.error(f"cannot generate test case, error: {e}")
            raise RuntimeError(f"cannot generate test case, error: {e}")
        


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
            self.err_msg = str(e)
            self.status = TaskStatus.FAILED

    def run_task_with_test(self, user_input: str):
        """
        run task with generating test case
        """

        try:
            test_case_type = self._select_test_case_type(user_input)
            test_case = self._generate_test_case(test_case_type)
            medical_record = self._extract_medical_record_info(test_case.medical_record_text)
            mdc_code = self._get_mdc_code(test_case.medical_record_text, medical_record)
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
            self.result = DrgResultWithTestCase(
                medical_record_text=test_case.medical_record_text,
                expected_result=test_case.expected_result,
                test_result=final_result
            )
            self.status = TaskStatus.SUCCESS
        except Exception as e:
            self.err_msg = str(e)
            self.status = TaskStatus.FAILED
