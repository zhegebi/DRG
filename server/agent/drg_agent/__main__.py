import uuid
import asyncio

from .task import Task
from .models import DrgResult, DrgResultWithTestCase



############### test DRG agent ######################
print("********test case 1: test DRG agent *********")
medical_record_text = """
    "性别": "女",
    "年龄": 55,
    "主要诊断": {
      "疾病名称": "胆管狭窄",
      "疾病编码": "K83.105"
    },
    "次要诊断列表": [
      { "疾病名称": "梗阻性黄疸","疾病编码": "K83.109" },
      { "疾病名称": "胆管扩张", "疾病编码": "K83.807" },
      { "疾病名称": "腹腔粘连", "疾病编码": "K66.007" },
      { "疾病名称": "更换胆管引流管", "疾病编码": "Z43.402" }
    ],
    "主要手术":  { "手术名称": "胆总管切除术", "手术编码": "51.6303", "手术级别": 3 },
    "其他手术列表": [
      { "手术名称": "胆管空肠吻合术", "手术编码": "51.3901", "手术级别": 3 },
      { "手术名称": "腹腔粘连松解术", "手术编码": "54.5901", "手术级别": 3 },
      { "手术名称": "颈内静脉穿刺中心静脉置管术", "手术编码": "38.9302", "手术级别": 2},
      { "手术名称": "胆管引流管置换术", "手术编码": "97.0501", "手术级别": 2}
    ]
"""
task_obj1 = Task(
    id = uuid.uuid4(),
    name = """
        "性别": "女","年龄": 55,
    """,
    user_input=medical_record_text,
    user_id = -1
)
asyncio.run(task_obj1.run_task_without_test(medical_record_text))
task_result1 = task_obj1.result
if isinstance(task_result1, DrgResult):
    print(task_result1.reason)



################### test DRG test generating agent ######################
print("********test case 2: test DRG test generating agent(normal case) *********")
user_input1 = "请给我生成一个正常情况的测试用例"
task_obj2 = Task(
    id=uuid.uuid4(),
    name="请给我生成一个正常情况的测试用例",
    user_input=user_input1,
    should_generate_test=True,
    user_id = -1
)
asyncio.run(task_obj2.run_task_with_test(user_input1))
task_result2 = task_obj2.result
if isinstance(task_result2, DrgResultWithTestCase):
    print("medical_record_text:", task_result2.medical_record_text)
    print("expected_result:", task_result2.expected_result)
    print("test_result:", task_result2.test_result)


print("********test case 3: test DRG test generating agent(boundary case) *********")
user_input2 = "请给我生成一个边界情况的测试用例"
task_obj3 = Task(
    id=uuid.uuid4(),
    name="请给我生成一个边界情况的测试用例",
    user_input=user_input2,
    should_generate_test=True,
    user_id = -1
)
asyncio.run(task_obj3.run_task_with_test(user_input2))
task_result3 = task_obj3.result
if isinstance(task_result3, DrgResultWithTestCase):
    print("medical_record_text:", task_result3.medical_record_text)
    print("expected_result:", task_result3.expected_result)
    print("test_result:", task_result3.test_result)


print("********test case 4: test DRG test generating agent(abnormal case) *********")
user_input3 = "请给我生成一个异常情况的测试用例"
task_obj4 = Task(
    id=uuid.uuid4(),
    name="请给我生成一个异常情况的测试用例",
    user_input=user_input3,
    should_generate_test=True,
    user_id = -1
)
asyncio.run(task_obj4.run_task_with_test(user_input3))
task_result4 = task_obj4.result
if isinstance(task_result4, DrgResultWithTestCase):
    print("medical_record_text:", task_result4.medical_record_text)
    print("expected_result:", task_result4.expected_result)
    print("test_result:", task_result4.test_result)
    print("error message:", task_obj4.err_msg)
