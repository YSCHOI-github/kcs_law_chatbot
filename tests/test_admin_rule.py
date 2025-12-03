import os
from adminapi import AdminAPI
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("dotenv not installed. Using system environment variables.")

def test_admin_rule_download(rule_name: str):
    """
    Test downloading an admin rule with detailed diagnostics
    """
    # Initialize API with LAW_API_KEY from environment
    api_key = os.getenv("LAW_API_KEY")
    if not api_key:
        print("ERROR: LAW_API_KEY environment variable not set")
        api_key = input("Please enter LAW_API_KEY: ").strip()
        if not api_key:
            print("ERROR: No API key provided. Exiting.")
            return

    admin_api = AdminAPI(api_key)

    print(f"Testing download for: {rule_name}")
    print("=" * 80)

    # Step 1: Search for admin rule ID
    print("\n[STEP 1] Searching for admin rule ID...")
    rule_id, found_name = admin_api.search_admin_rule_id(rule_name)

    if not rule_id:
        print(f"FAILURE: No admin rule found for query: {rule_name}")
        print("Possible reasons:")
        print("- Rule name is incorrect or doesn't match API database")
        print("- Rule is not in the admin rules database (might be a regular law)")
        print("- API connection issue")
        return

    print(f"SUCCESS: Found rule ID: {rule_id}")
    print(f"   Rule name: {found_name}")

    # Step 2: Fetch admin rule data
    print("\n[STEP 2] Fetching admin rule data...")
    rule_data = admin_api.get_admin_rule_json(rule_id)

    if not rule_data:
        print(f"FAILURE: No data returned for rule ID: {rule_id}")
        return

    print(f"SUCCESS: Received data")
    print(f"   Data keys: {list(rule_data.keys())}")

    # Output raw JSON for inspection
    print("\n[RAW API RESPONSE]")
    print(json.dumps(rule_data, ensure_ascii=False, indent=2)[:2000])
    print("..." if len(json.dumps(rule_data)) > 2000 else "")

    # Step 3: Extract text
    print("\n[STEP 3] Extracting text from rule data...")
    text = admin_api.extract_text_from_rule_data(rule_data)

    if not text:
        print(f"FAILURE: No text extracted from rule data")
        return

    print(f"SUCCESS: Extracted text")
    print(f"   Text length: {len(text)} characters")
    print(f"   First 500 chars:\n{text[:500]}")

    if len(text) < 50:
        print(f"\nWARNING: Text is very short ({len(text)} chars < 50 threshold)")
        print("   This will cause download_admin_rule_as_json() to return empty data")

    # Step 4: Attempt full download
    print("\n[STEP 4] Attempting full download with parsing...")
    result = admin_api.download_admin_rule_as_json(rule_name)

    if not result:
        print(f"FAILURE: download_admin_rule_as_json() returned None")
        return

    article_count = len(result.get("조문", []))
    print(f"SUCCESS: Downloaded and parsed")
    print(f"   Articles found: {article_count}")

    if article_count == 0:
        print(f"\nWARNING: No articles extracted by parser")
        print("   Possible reasons:")
        print("   - Text format doesn't match article parsing patterns")
        print("   - Text is in unusual format")
        print("   - Parser regex patterns need adjustment")

    # Output parsed result
    print("\n[PARSED RESULT]")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:1000])
    print("..." if len(json.dumps(result)) > 1000 else "")

if __name__ == "__main__":
    # Test the problematic rule
    test_admin_rule_download("공무원임용규칙")
