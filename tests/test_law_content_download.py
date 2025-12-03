import os
import requests
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_law_content_download(law_id: str, law_name: str):
    """Test downloading actual law content by ID"""

    api_key = os.getenv("LAW_API_KEY")
    if not api_key:
        api_key = input("Please enter LAW_API_KEY: ").strip()
        if not api_key:
            return

    base_url = "http://www.law.go.kr/DRF/lawService.do"

    print(f"\n{'='*80}")
    print(f"Testing Law Content Download")
    print(f"Law ID: {law_id}")
    print(f"Law Name: {law_name}")
    print(f"{'='*80}\n")

    params = {
        "OC": api_key,
        "target": "law",
        "type": "JSON",
        "ID": law_id
    }

    try:
        print("Requesting law content from API...")
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        print(f"Response status: {response.status_code}")
        print(f"Response size: {len(response.content)} bytes")

        # Try to parse JSON
        try:
            data = response.json()
            print("\nJSON parsing: SUCCESS")

            # Check structure
            if "법령" in data:
                print("Found '법령' key in response")

                # Check basic info
                basic_info = data.get("법령", {}).get("기본정보", {})
                if basic_info:
                    print(f"\nBasic Info:")
                    print(f"  법령ID: {basic_info.get('법령ID', 'N/A')}")
                    print(f"  법령명: {basic_info.get('법령명_한글', 'N/A')}")

                # Check articles
                law_content = data.get("법령", {})
                if "조문" in law_content:
                    articles = law_content["조문"]
                    if "조문단위" in articles:
                        article_list = articles["조문단위"]
                        if isinstance(article_list, dict):
                            article_count = 1
                        else:
                            article_count = len(article_list)
                        print(f"\nArticles found: {article_count}")
                        print("SUCCESS: Law content downloaded successfully")
                    else:
                        print("\nWARNING: No '조문단위' in articles")
                        print("Response structure:")
                        print(json.dumps(articles, ensure_ascii=False, indent=2)[:500])
                else:
                    print("\nERROR: No '조문' key in law content")
                    print("Available keys:", list(law_content.keys()))
            else:
                print("\nERROR: No '법령' key in response")
                print("Response structure:")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])

        except json.JSONDecodeError as e:
            print(f"\nERROR: Failed to parse JSON - {e}")
            print("First 500 chars of response:")
            print(response.text[:500])

    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Request failed - {e}")
    except Exception as e:
        print(f"\nERROR: Unexpected error - {e}")
        import traceback
        traceback.print_exc()

def main():
    # Test the law that failed to download
    test_cases = [
        ("013993", "중대재해 처벌 등에 관한 법률"),
        ("014159", "중대재해 처벌 등에 관한 법률 시행령"),  # This one succeeded, for comparison
    ]

    for law_id, law_name in test_cases:
        test_law_content_download(law_id, law_name)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
