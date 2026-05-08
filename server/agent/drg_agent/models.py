from pydantic import BaseModel, Field
from typing import Dict, List
from enum import Enum
from pathlib import Path


# type that will be used in other class
class complication(str, Enum):
    CC = "cc"
    MCC = "mcc"
    NO = "no"
    ANY = "any"
    CC_or_MCC = "cc_or_mcc"

class drg_data(BaseModel):
    code: str
    name: str
    type: complication

class procedure_to_adrg_result(BaseModel):
    adrg_code: str
    mdc_code: str

class mcc_data(BaseModel):
    code: str
    name: str
    exclusion_table: str

class cc_data(BaseModel):
    code: str
    name: str
    exclusion_table: str

class exclusion_table_data(BaseModel):
    diag_code: str = Field(alias="code")
    diag_name: str = Field(alias="name")


class mdc_adrg_drg(BaseModel):
    """
    {
        mdc: {
            "mdc_code": "mdc_name"
        },
        adrg: {
            "adrg_code": "adrg_name"
        },
        drg: {
            "adrg_code": [drg_data]
        }
    }
    """
    mdc: Dict[str, str]
    adrg: Dict[str, str]
    drg: Dict[str, List[drg_data]]

class diag_to_mdc(BaseModel):
    """
    {
        data: 
        {
            "diag_code": ["mdc_code"]
        }
    }
    """
    data: Dict[str, List[str]]

class procedure_to_adrg(BaseModel):
    """
    {
        data: 
        {
            "procedure_code": [procedure_to_adrg_result]
        }
    }
    """
    data: Dict[str, List[procedure_to_adrg_result]]

class mcc_and_cc(BaseModel):
    """
    {
        mcc: [mcc_data],
        cc: [cc_data],
        exclusion_tables: {
            "表xxxx": [exclusion_table_data]
        }
    }
    """
    mcc: List[mcc_data]
    cc: List[cc_data]
    exclusion_tables: Dict[str, List[exclusion_table_data]]



def load_data(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        data_json = f.read()
    return data_json

CURRENT_DIR = Path(__file__).parent

mdc_adrg_drg_json = load_data(CURRENT_DIR / "mdc_adrg_drg.json")
MDC_ADRG_DRG = mdc_adrg_drg.model_validate_json(mdc_adrg_drg_json)

diag_to_mdc_json = load_data(CURRENT_DIR / "diagnosis_to_mdc.json")
DIAG_TO_MDC = diag_to_mdc.model_validate_json(diag_to_mdc_json)

procedure_to_adrg_json = load_data(CURRENT_DIR / "procedure_to_adrg.json")
PROCEDURE_TO_ADRG = procedure_to_adrg.model_validate_json(procedure_to_adrg_json)

mcc_and_cc_json = load_data(CURRENT_DIR / "MCC_and_CC.json")
MCC_AND_CC = mcc_and_cc.model_validate_json(mcc_and_cc_json)