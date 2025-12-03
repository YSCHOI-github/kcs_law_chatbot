import os
from adminapi import AdminAPI
from lawapi import LawAPI
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_both_apis(rule_name: str):
    """Test if rule exists in Law API, Admin API, or both"""

    api_key = os.getenv("LAW_API_KEY")
    if not api_key:
        api_key = input("Please enter LAW_API_KEY: ").strip()
        if not api_key:
            return

    print(f"Searching for: {rule_name}")
    print("=" * 80)

    # Test 1: Law API
    print("\n[TEST 1] Searching in LAW API (target=law)...")
    print("This API contains: 법률, 대통령령, 시행령, 부령, 시행규칙")

    law_api = LawAPI(api_key)
    law_id, law_name = law_api.search_law_id(rule_name)

    if law_id:
        print(f"FOUND in Law API!")
        print(f"   ID: {law_id}")
        print(f"   Name: {law_name}")
        print(f"   Match: {'EXACT' if rule_name == law_name else 'PARTIAL'}")

        # Try to download a sample
        print("\n   Fetching sample data...")
        try:
            law_data = law_api.download_law_as_json(rule_name)
            if law_data and law_data.get('조문'):
                article_count = len(law_data['조문'])
                print(f"   Articles found: {article_count}")
                if article_count > 0:
                    first_article = law_data['조문'][0]
                    print(f"   First article: {first_article.get('조번호', 'N/A')}")
        except Exception as e:
            print(f"   Error fetching: {e}")
    else:
        print(f"NOT FOUND in Law API")

    # Test 2: Admin API
    print("\n[TEST 2] Searching in ADMIN API (target=admrul)...")
    print("This API contains: 훈령, 예규, 지침, 고시")

    admin_api = AdminAPI(api_key)
    admin_id, admin_name = admin_api.search_admin_rule_id(rule_name)

    if admin_id:
        print(f"FOUND in Admin API!")
        print(f"   ID: {admin_id}")
        print(f"   Name: {admin_name}")
        print(f"   Match: {'EXACT' if rule_name == admin_name else 'PARTIAL'}")

        # Try to download a sample
        print("\n   Fetching sample data...")
        try:
            admin_data = admin_api.download_admin_rule_as_json(rule_name)
            if admin_data and admin_data.get('조문'):
                article_count = len(admin_data['조문'])
                print(f"   Articles found: {article_count}")
                if article_count > 0:
                    first_article = admin_data['조문'][0]
                    print(f"   First article: {first_article.get('조번호', 'N/A')}")
        except Exception as e:
            print(f"   Error fetching: {e}")
    else:
        print(f"NOT FOUND in Admin API")

    # Analysis
    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)

    if law_id and admin_id:
        print("WARNING: Found in BOTH APIs!")
        print(f"   Law API: {law_name} (ID: {law_id})")
        print(f"   Admin API: {admin_name} (ID: {admin_id})")
        if rule_name == law_name:
            print(f"\nUse LAW API (exact match)")
        elif rule_name == admin_name:
            print(f"\nUse ADMIN API (exact match)")
        else:
            print(f"\nNeither is exact match - manual verification needed")

    elif law_id:
        if rule_name == law_name:
            print(f"CONFIRMED: This is a LAW document (법령)")
            print(f"   Use: LawAPI.download_law_as_json('{rule_name}')")
            print(f"   Package config: Add to 'laws' list, NOT 'admin_rules'")
        else:
            print(f"WARNING: Found in Law API but name doesn't match")
            print(f"   Searched: {rule_name}")
            print(f"   Found: {law_name}")
            print(f"   This may be a fuzzy search result - verify manually")

    elif admin_id:
        if rule_name == admin_name:
            print(f"CONFIRMED: This is an ADMIN RULE (행정규칙)")
            print(f"   Use: AdminAPI.download_admin_rule_as_json('{rule_name}')")
            print(f"   Package config: Add to 'admin_rules' list, NOT 'laws'")
        else:
            print(f"WARNING: Found in Admin API but name doesn't match")
            print(f"   Searched: {rule_name}")
            print(f"   Found: {admin_name}")
            print(f"   This may be a fuzzy search result - verify manually")

    else:
        print(f"ERROR: Not found in either API!")
        print(f"   Possible reasons:")
        print(f"   - Document name is incorrect")
        print(f"   - Document doesn't exist in database")
        print(f"   - API connection issue")

if __name__ == "__main__":
    test_both_apis("공무원임용규칙")
