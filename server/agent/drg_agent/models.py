from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path


################ drg rule models ################
# assistant models
class Complication(str, Enum):
    CC = "cc"
    MCC = "mcc"
    NO = "no"
    ANY = "any"
    CC_or_MCC = "cc_or_mcc"

class DrgData(BaseModel):
    code: str
    name: str
    type: Complication

class ProcedureToAdrgResult(BaseModel):
    adrg_code: str
    mdc_code: str

class MccAndCcData(BaseModel):
    code: str
    exclusion_table: str


class MdcAdrgDrg(BaseModel):
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
    drg: Dict[str, List[DrgData]]

class DiagToMdc(BaseModel):
    """
    {
        data: 
        {
            "diag_code": ["mdc_code"]
        }
    }
    """
    data: Dict[str, List[str]]

class ProcedureToAdrg(BaseModel):
    """
    {
        data: 
        {
            "procedure_code": [procedure_to_adrg_result]
        }
    }
    """
    data: Dict[str, List[ProcedureToAdrgResult]]

class MccAndCc(BaseModel):
    """
    {
        mcc: [mcc_data],
        cc: [cc_data],
        exclusion_tables: {
            "表xxxx": ["diag_code"]
        }
    }
    """
    mcc: List[MccAndCcData]
    cc: List[MccAndCcData]
    exclusion_tables: Dict[str, List[str]]

class NameToCode(BaseModel):
    """
    {
        "diagnosis": 
        {
            "name": "code"
        },
        "procedure":
        {
            "name": "code"
        }
    }
    """
    diagnosis: Dict[str, str]
    procedure: Dict[str, str]


################ medical record models ################
# assistant models
class GeneralInformation(BaseModel):
    """
    diagnosis and procedure data structure
    """
    code: Optional[str] = None
    name: Optional[str] = None


class MedicalRecord(BaseModel):
    primary_diagnosis: GeneralInformation
    secondary_diagnosis_list: List[GeneralInformation] = []
    primary_procedure: GeneralInformation
    other_procedures: List[GeneralInformation] = []



# load drg rule data from json file
def load_data(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        data_json = f.read()
    return data_json

CURRENT_DIR = Path(__file__).parent

mdc_adrg_drg_json = load_data(CURRENT_DIR / "mdc_adrg_drg.json")
MDC_ADRG_DRG = MdcAdrgDrg.model_validate_json(mdc_adrg_drg_json)

diag_to_mdc_json = load_data(CURRENT_DIR / "diagnosis_to_mdc.json")
DIAG_TO_MDC = DiagToMdc.model_validate_json(diag_to_mdc_json)

procedure_to_adrg_json = load_data(CURRENT_DIR / "procedure_to_adrg.json")
PROCEDURE_TO_ADRG = ProcedureToAdrg.model_validate_json(procedure_to_adrg_json)

mcc_and_cc_json = load_data(CURRENT_DIR / "MCC_and_CC.json")
MCC_AND_CC = MccAndCc.model_validate_json(mcc_and_cc_json)

name_to_code_json = load_data(CURRENT_DIR / "name_to_code.json")
NAME_TO_CODE = NameToCode.model_validate_json(name_to_code_json)
