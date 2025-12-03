# 법령 패키지 사전 다운로드 스크립트
# 관세조사, 외환조사, 대외무역 3가지 패키지를 ./laws 폴더에 JSON으로 저장
# 3단 비교 법령 자동 다운로드 기능 포함

import os
import json
from lawapi import LawAPI, convert_law_data_to_chatbot_format
from adminapi import AdminAPI, convert_admin_rule_data_to_chatbot_format

# 환경변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("dotenv 모듈이 없습니다. 시스템 환경변수를 사용합니다.")

LAW_API_KEY = os.getenv('LAW_API_KEY')

# API 키가 없으면 사용자 입력 받기
if not LAW_API_KEY:
    LAW_API_KEY = input("LAW_API_KEY를 입력하세요: ").strip()

# 3가지 패키지 정의
PACKAGES = {
    "customs_investigation": {
        "name": "관세조사",
        "laws": [
            "관세법",
            "관세법 시행령", 
            "관세법 시행규칙"
        ],
        "admin_rules": [
            "관세평가 운영에 관한 고시",
            "관세조사 운영에 관한 훈령"
        ],
        "three_stage_laws": [
            "관세법"
        ]
    },
    "foreign_exchange_investigation": {
        "name": "외환조사",
        "laws": [
            "외국환거래법",
            "외국환거래법 시행령"
        ],
        "admin_rules": [
            "외국환거래규정"
        ],
        "three_stage_laws": [
            "외국환거래법"
        ]
    },
    "foreign_trade": {
        "name": "대외무역",
        "laws": [
            "대외무역법",
            "대외무역법 시행령"
        ],
        "admin_rules": [
            "대외무역관리규정"
        ],
        "three_stage_laws": [
            "대외무역법"
        ]
    },
    "free_trade_agreement": {
        "name": "자유무역협정",
        "laws": [
            "자유무역협정 이행을 위한 관세법의 특례에 관한 법률",
            "자유무역협정 이행을 위한 관세법의 특례에 관한 법률 시행령",
            "자유무역협정 이행을 위한 관세법의 특례에 관한 법률 시행규칙"
        ],
        "admin_rules": [
            "자유무역협정 이행을 위한 관세법의 특례에 관한 법률 사무처리에 관한 고시",
            "원산지 조사 운영에 관한 훈령",
            "자유무역협정 원산지인증수출자 운영에 관한 고시"
        ],
        "three_stage_laws": [
            "자유무역협정 이행을 위한 관세법의 특례에 관한 법률"
        ]
    },
    "refund": {
        "name": "환급",
        "laws": [
            "수출용 원재료에 대한 관세 등 환급에 관한 특례법",
            "수출용 원재료에 대한 관세 등 환급에 관한 특례법 시행령",
            "수출용 원재료에 대한 관세 등 환급에 관한 특례법 시행규칙"
        ],
        "admin_rules": [
            "수출용 원재료에 대한 관세 등 환급사무처리에 관한 고시",
            "위탁가공 수출물품에 대한 관세 등 환급처리에 관한 예규",
            "수출용 원재료에 대한 관세 등 환급사무에 관한 훈령",
            "수입원재료에 대한 환급방법 조정에 관한 고시",
            "대체수출물품 관세환급에 따른 수출입통관절차 및 환급처리에 관한 예규",
            "수입물품에 대한 개별소비세와 주세 등의 환급에 관한 고시"
        ],
        "three_stage_laws": [
            "수출용 원재료에 대한 관세 등 환급에 관한 특례법"
        ]
    },
    "professional_position_management": {
        "name": "전문직위/보직관리",
        "laws": [
            "국가공무원법",
            "공무원임용령"
        ],
        "admin_rules": [
            "세관공무원 인사관리에 관한 훈령",
            "관세청 직위유형별 보직관리 지침",
            "관세청 전자보직제도 운영에 관한 예규",
            "공무원임용규칙"
        ],
        "three_stage_laws": [
            "국가공무원법"
        ]
    },
    "special_promotion": {
        "name": "특별승급",
        "laws": [
            "공무원 보수규정"
        ],
        "admin_rules": [
            "공무원보수 등의 업무지침",
            "세관공무원 인사관리에 관한 훈령"
        ],
        "three_stage_laws": []
    },
    "training": {
        "name": "교육훈련",
        "laws": [
            "공무원 인재개발법",
            "공무원 인재개발법 시행령"
        ],
        "admin_rules": [
            "공무원 인재개발 업무처리지침",
            "관세청 인재개발에 관한 훈령"
        ],
        "three_stage_laws": [
            "공무원 인재개발법"
        ]
    },
    "performance_evaluation": {
        "name": "성과평가",
        "laws": [
            "국가공무원법",
            "공무원 성과평가 등에 관한 규정"
        ],
        "admin_rules": [
            "공무원 성과평가 등에 관한 지침",
            "세관공무원 인사관리에 관한 훈령",
            "근무실적평가제도 운영지침"
        ],
        "three_stage_laws": [
            "국가공무원법"
        ]
    },
    "disciplinary_action": {
        "name": "징계",
        "laws": [
            "국가공무원법",
            "공무원 징계령",
            "공무원 징계령 시행규칙"
        ],
        "admin_rules": [
            "관세공무원 상벌에 관한 훈령"
        ],
        "three_stage_laws": [
            "국가공무원법"
        ]
    },
    "service_discipline": {
        "name": "복무",
        "laws": [
            "국가공무원법",
            "국가공무원 복무규정",
            "국가공무원 복무규칙"
        ],
        "admin_rules": [
            "국가공무원 복무징계 관련 예규"
        ],
        "three_stage_laws": [
            "국가공무원법"
        ]
    },
    "government_contract": {
        "name": "계약",
        "laws": [
            "국가를 당사자로 하는 계약에 관한 법률",
            "국가를 당사자로 하는 계약에 관한 법률 시행령",
            "국가를 당사자로 하는 계약에 관한 법률 시행규칙"
        ],
        "admin_rules": [
            "국가를 당사자로 하는 계약에 관한 법률 시행령의 한시적 특례 적용기간에 관한 고시",
            "관세청 협상에 의한 계약 제안서 평가 업무처리 규정"
        ],
        "three_stage_laws": [
            "국가를 당사자로 하는 계약에 관한 법률"
        ]
    },
    "accounting_officer": {
        "name": "회계관계공무원",
        "laws": [
            "회계관계직원 등의 책임에 관한 법률",
            "회계관계직원 등의 책임에 관한 법률 시행령"
        ],
        "admin_rules": [
            "관세청 회계직공무원 지정 및 재정보증에 관한 훈령"
        ],
        "three_stage_laws": [
            "회계관계직원 등의 책임에 관한 법률"
        ]
    },
    "serious_accident": {
        "name": "중대재해",
        "laws": [
            "중대재해 처벌 등에 관한 법률",
            "중대재해 처벌 등에 관한 법률 시행령",
            "산업안전보건법",
            "산업안전보건법 시행령",
            "산업안전보건법 시행규칙",
            "산업안전보건기준에 관한 규칙"
        ],
        "admin_rules": [
            "안전보건관리전문기관 및 건설재해예방전문지도기관 관리규정",
            "안전보건교육규정"
        ],
        "three_stage_laws": [
            "중대재해 처벌 등에 관한 법률",
            "산업안전보건법"
        ]
    }
}

def download_law(law_api, law_name):
    """법령 다운로드"""
    print(f"법령 다운로드 중: {law_name}")
    try:
        law_data = law_api.download_law_as_json(law_name)
        if law_data:
            chatbot_data = convert_law_data_to_chatbot_format(law_data)
            print(f"✅ {law_name} 다운로드 완료 ({len(chatbot_data)}개 조문)")
            return chatbot_data
        else:
            print(f"❌ {law_name} 다운로드 실패: 데이터 없음")
            return None
    except Exception as e:
        print(f"❌ {law_name} 다운로드 실패: {str(e)}")
        return None

def download_admin_rule(admin_api, admin_name):
    """행정규칙 다운로드"""
    print(f"행정규칙 다운로드 중: {admin_name}")
    try:
        admin_data = admin_api.download_admin_rule_as_json(admin_name)
        if admin_data:
            chatbot_data = convert_admin_rule_data_to_chatbot_format(admin_data)
            print(f"✅ {admin_name} 다운로드 완료 ({len(chatbot_data)}개 조문)")
            return chatbot_data
        else:
            print(f"❌ {admin_name} 다운로드 실패: 데이터 없음")
            return None
    except Exception as e:
        print(f"❌ {admin_name} 다운로드 실패: {str(e)}")
        return None

def download_three_stage_comparison(law_api, law_name):
    """3단 비교 법령 다운로드"""
    print(f"3단 비교 법령 다운로드 중: {law_name}")
    try:
        three_stage_data = law_api.download_three_stage_comparison_as_json(law_name)
        if three_stage_data:
            print(f"✅ {law_name} 3단 비교 다운로드 완료 ({len(three_stage_data)}개 조문)")
            return three_stage_data
        else:
            print(f"❌ {law_name} 3단 비교 다운로드 실패: 데이터 없음")
            return None
    except Exception as e:
        print(f"❌ {law_name} 3단 비교 다운로드 실패: {str(e)}")
        return None

def download_package(package_id, package_info, law_api, admin_api):
    """패키지 전체 다운로드"""
    print(f"\n📦 {package_info['name']} 패키지 다운로드 시작")
    print("=" * 50)
    
    package_data = {}
    
    # 법령 다운로드
    for law_name in package_info["laws"]:
        data = download_law(law_api, law_name)
        if data:
            package_data[law_name] = {
                "type": "law",
                "data": data
            }
    
    # 행정규칙 다운로드
    for admin_name in package_info["admin_rules"]:
        data = download_admin_rule(admin_api, admin_name)
        if data:
            package_data[admin_name] = {
                "type": "admin",
                "data": data
            }
    
    # 3단 비교 법령 다운로드
    for law_name in package_info.get("three_stage_laws", []):
        data = download_three_stage_comparison(law_api, law_name)
        if data:
            three_stage_name = f"{law_name} (3단비교)"
            package_data[three_stage_name] = {
                "type": "three_stage",
                "data": data
            }
    
    # JSON 파일로 저장
    laws_dir = "./laws"
    os.makedirs(laws_dir, exist_ok=True)
    
    filename = f"{laws_dir}/{package_id}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(package_data, f, ensure_ascii=False, indent=2)
    
    total_laws = len(package_data)
    total_articles = sum(len(item["data"]) for item in package_data.values())
    
    print(f"💾 {package_info['name']} 패키지 저장 완료: {filename}")
    print(f"📊 총 {total_laws}개 법령, {total_articles}개 조문")
    
    return package_data

def main():
    """메인 함수"""
    if not LAW_API_KEY:
        print("❌ 오류: LAW_API_KEY 환경변수가 필요합니다.")
        return

    print("🚀 법령 패키지 다운로드 시작")
    print(f"API 키 확인 - LAW: {'✅' if LAW_API_KEY else '❌'}")

    # API 클라이언트 초기화 (LAW_API_KEY는 행정규칙 API에도 사용됨)
    law_api = LawAPI(LAW_API_KEY)
    admin_api = AdminAPI(LAW_API_KEY)
    
    # 패키지별 다운로드
    for package_id, package_info in PACKAGES.items():
        try:
            download_package(package_id, package_info, law_api, admin_api)
        except Exception as e:
            print(f"❌ {package_info['name']} 패키지 다운로드 실패: {str(e)}")
    
    print("\n🎉 모든 패키지 다운로드 완료!")
    print("./laws 폴더를 확인하세요.")

if __name__ == "__main__":
    main()