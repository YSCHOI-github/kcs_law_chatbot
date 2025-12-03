import os
import requests
import xml.etree.ElementTree as ET

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def search_all_results(query: str, target: str, api_name: str):
    """Search and list ALL results from the API"""

    api_key = os.getenv("LAW_API_KEY")
    if not api_key:
        api_key = input("Please enter LAW_API_KEY: ").strip()
        if not api_key:
            return

    base_url = "http://www.law.go.kr/DRF/lawSearch.do"

    print(f"\n{'='*80}")
    print(f"Searching in {api_name}")
    print(f"Query: {query}")
    print(f"Target: {target}")
    print(f"{'='*80}\n")

    # Request more results (display=100 to get up to 100 results)
    params = {
        "OC": api_key,
        "target": target,
        "type": "XML",
        "query": query,
        "display": 100  # Get up to 100 results
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        # Get total count
        total_count = root.findtext("totalCnt", "0")
        print(f"Total results found: {total_count}")
        print()

        # Different XML tags for law vs admin
        if target == "law":
            items = root.findall("law")
            id_tag = "법령ID"
            name_tag = "법령명한글"
            date_tag = "공포일자"
        else:  # admrul
            items = root.findall("admrul")
            id_tag = "행정규칙일련번호"
            name_tag = "행정규칙명"
            date_tag = "제정일자"

        if not items:
            print("No results found.")
            return

        # List all results
        for idx, item in enumerate(items, 1):
            item_id = item.findtext(id_tag, "N/A")
            item_name = item.findtext(name_tag, "N/A")
            item_date = item.findtext(date_tag, "N/A")

            # Check if exact match
            match_type = "EXACT" if query == item_name else "PARTIAL"
            match_symbol = "✅" if match_type == "EXACT" else "📌"

            print(f"{match_symbol} Result {idx}:")
            print(f"   ID: {item_id}")
            print(f"   Name: {item_name}")
            print(f"   Date: {item_date}")
            print(f"   Match: {match_type}")
            print()

    except Exception as e:
        print(f"Error: {e}")

def main():
    query = "공무원임용규칙"

    # Search in Law API
    search_all_results(query, "law", "LAW API (법령 - 법률, 시행령, 시행규칙)")

    # Search in Admin API
    search_all_results(query, "admrul", "ADMIN API (행정규칙 - 훈령, 예규, 지침, 고시)")

    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print("✅ = Exact match (name matches query exactly)")
    print("📌 = Partial match (fuzzy search result)")
    print("\nLook for results marked with ✅ for exact matches.")
    print("If no exact match, verify document names manually.")

if __name__ == "__main__":
    main()
