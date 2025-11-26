#!/usr/bin/env python3
"""
Test Claude Response Format

Direct test to see what Claude returns for area discovery.
"""
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.collection.prompts import generate_community_collection_prompt
from anthropic import Anthropic

def test_area_discovery_prompt():
    """Test what Claude returns for area discovery"""
    print("\n" + "="*60)
    print("Testing Claude Response Format for Area Discovery")
    print("="*60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    print(f"✅ API Key found: {api_key[:20]}...")

    # Generate area discovery prompt (no community name)
    location = "Dallas, TX"
    prompt = generate_community_collection_prompt(None, location)

    print(f"\n📋 Prompt Preview (first 500 chars):")
    print(prompt[:500] + "...")

    # Call Claude
    print(f"\n🔍 Calling Claude Sonnet 4.5...")
    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=16000,  # Increased for area discovery
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    response_text = message.content[0].text

    print(f"\n📊 Response Stats:")
    print(f"   Input tokens: {message.usage.input_tokens}")
    print(f"   Output tokens: {message.usage.output_tokens}")
    print(f"   Response length: {len(response_text)} chars")

    print(f"\n📝 Raw Response (first 1000 chars):")
    print(response_text[:1000])

    # Save full response to file for analysis
    with open("claude_response_full.txt", "w") as f:
        f.write(response_text)
    print(f"\n💾 Full response saved to: claude_response_full.txt")

    # Try to parse as JSON (with extraction logic like base_collector)
    print(f"\n🔧 Attempting to parse as JSON...")

    def extract_json(text):
        """Extract JSON from Claude response (same logic as base_collector)"""
        import re
        try:
            # First try direct parsing
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass

            # Try to find any JSON object in the response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    # Try to repair incomplete JSON
                    repaired = json_text.rstrip()
                    open_braces = repaired.count('{') - repaired.count('}')
                    open_brackets = repaired.count('[') - repaired.count(']')

                    # Close arrays first, then objects
                    for _ in range(open_brackets):
                        repaired += ']'
                    for _ in range(open_braces):
                        repaired += '}'

                    try:
                        parsed = json.loads(repaired)
                        print(f"   ⚠️  Repaired incomplete JSON (added {open_brackets} ] and {open_braces} }})")
                        return parsed
                    except json.JSONDecodeError:
                        pass

            return None

    data = extract_json(response_text)

    if data:
        print(f"✅ Successfully extracted and parsed JSON")
        print(f"   Keys: {list(data.keys())}")

        if "communities" in data:
            communities = data["communities"]
            print(f"   ✅ Found 'communities' array with {len(communities)} items")

            if len(communities) > 0:
                print(f"\n   First 3 communities:")
                for i, community in enumerate(communities[:3], 1):
                    print(f"      {i}. {community.get('name', 'N/A')} - {community.get('city', 'N/A')}, {community.get('state', 'N/A')}")
        else:
            print(f"   ⚠️  No 'communities' key found")
            print(f"   Available keys: {list(data.keys())}")

            # Check if it's single community format
            if "name" in data:
                print(f"   ℹ️  Looks like single community format")
                print(f"      Name: {data.get('name')}")
    else:
        print(f"❌ Failed to extract JSON from response")
        print(f"   Response might not be valid JSON")

    print("\n" + "="*60)

if __name__ == "__main__":
    test_area_discovery_prompt()
