import sys
import os
import unittest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai.models import get_client, GeminiClientWrapper, MODEL_FLASH
from utils.ai.query_expander import QueryExpander

class TestGeminiErrorHandling(unittest.TestCase):
    def test_client_initialization(self):
        print("\nTesting Client Initialization...")
        client = get_client()
        self.assertIsInstance(client, GeminiClientWrapper)
        print("Success.")

    def test_simple_generation(self):
        print("\nTesting Simple Generation...")
        client = get_client()
        try:
            # Using a very simple prompt to minimize token usage/latency
            response = client.generate_content("Say 'OK'", model=MODEL_FLASH)
            print(f"Response: {response}")
            self.assertIsNotNone(response)
        except Exception as e:
            self.fail(f"Generation failed: {e}")

    def test_query_expander_usage(self):
        print("\nTesting QueryExpander Usage...")
        try:
            qe = QueryExpander()
            # We won't call the API here to save time/cost in this quick check, 
            # unless test_simple_generation passes and we want to be thorough.
            # But just init confirms imports are correct.
            self.assertIsInstance(qe, QueryExpander)
            print("QueryExpander initialized successfully.")
        except Exception as e:
            self.fail(f"QueryExpander init failed: {e}")

if __name__ == '__main__':
    unittest.main()
