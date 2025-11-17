"""
Example script demonstrating GPT-5 API usage with LitRelevanceAI.

This script shows how to use GPT-5 and o1 models with the updated AIClient.
"""

from litrx.ai_client import AIClient
from litrx.config import load_env_file

# Load environment variables
load_env_file()

def example_gpt5_basic():
    """Basic GPT-5 usage example."""
    print("=" * 60)
    print("Example 1: Basic GPT-5 Usage")
    print("=" * 60)

    config = {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "gpt-5",
        "OPENAI_API_KEY": "",  # Will be loaded from .env
        "VERBOSITY": "medium",
        "REASONING_EFFORT": "medium"
    }

    client = AIClient(config)

    messages = [
        {"role": "user", "content": "What is the significance of literature review in research?"}
    ]

    print("\nSending request to GPT-5...")
    response = client.request(messages)

    print("\nResponse:")
    print(response["choices"][0]["message"]["content"])
    print("\n")


def example_gpt5_with_different_verbosity():
    """Example showing different verbosity levels."""
    print("=" * 60)
    print("Example 2: Testing Different Verbosity Levels")
    print("=" * 60)

    for verbosity in ["low", "medium", "high"]:
        print(f"\n--- Verbosity: {verbosity} ---")

        config = {
            "AI_SERVICE": "openai",
            "MODEL_NAME": "gpt-5",
            "VERBOSITY": verbosity,
            "REASONING_EFFORT": "low"
        }

        client = AIClient(config)

        messages = [
            {"role": "user", "content": "Explain what a literature matrix is in one sentence."}
        ]

        response = client.request(messages)
        print(response["choices"][0]["message"]["content"])


def example_o1_model():
    """Example using o1 series model."""
    print("=" * 60)
    print("Example 3: Using o1 Model")
    print("=" * 60)

    config = {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "o1-preview",
        "VERBOSITY": "medium"
        # Note: o1 models don't support REASONING_EFFORT
    }

    client = AIClient(config)

    messages = [
        {"role": "user", "content": "What are the key steps in conducting a systematic literature review?"}
    ]

    print("\nSending request to o1-preview...")
    response = client.request(messages)

    print("\nResponse:")
    print(response["choices"][0]["message"]["content"])
    print("\n")


def example_backward_compatibility():
    """Example showing backward compatibility with GPT-4."""
    print("=" * 60)
    print("Example 4: Backward Compatibility with GPT-4")
    print("=" * 60)

    config = {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "gpt-4o",
        "TEMPERATURE": 0.3
        # GPT-4 uses old parameters like temperature
    }

    client = AIClient(config)

    messages = [
        {"role": "user", "content": "What is the purpose of abstract screening?"}
    ]

    print("\nSending request to GPT-4o...")
    response = client.request(messages)

    print("\nResponse:")
    print(response["choices"][0]["message"]["content"])
    print("\n")


def example_json_response():
    """Example requesting JSON formatted response."""
    print("=" * 60)
    print("Example 5: JSON Response with GPT-5")
    print("=" * 60)

    config = {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "gpt-5",
        "VERBOSITY": "low",
        "REASONING_EFFORT": "low"
    }

    client = AIClient(config)

    messages = [
        {
            "role": "user",
            "content": """Analyze the relevance of this paper title to machine learning research.
            Return in JSON format with fields: relevance_score (0-100), reason (brief explanation).

            Title: "Deep Learning Approaches for Natural Language Processing"
            """
        }
    ]

    print("\nSending request to GPT-5...")
    response = client.request(
        messages,
        response_format={"type": "json_object"}
    )

    print("\nResponse:")
    print(response["choices"][0]["message"]["content"])
    print("\n")


if __name__ == "__main__":
    import sys

    # Check if API key is configured
    from litrx.config import DEFAULT_CONFIG
    if not DEFAULT_CONFIG.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not configured in .env file")
        print("Please create a .env file with your API key:")
        print("  OPENAI_API_KEY=sk-...")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("GPT-5 API Examples for LitRelevanceAI")
    print("=" * 60)
    print("\nThese examples demonstrate the new GPT-5 features.")
    print("You can run individual examples or all of them.\n")

    examples = {
        "1": ("Basic GPT-5 Usage", example_gpt5_basic),
        "2": ("Different Verbosity Levels", example_gpt5_with_different_verbosity),
        "3": ("o1 Model Usage", example_o1_model),
        "4": ("GPT-4 Compatibility", example_backward_compatibility),
        "5": ("JSON Response", example_json_response),
        "all": ("Run All Examples", None)
    }

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        print("Available examples:")
        for key, (desc, _) in examples.items():
            print(f"  {key}. {desc}")
        print("\nUsage: python gpt5_example.py [1-5|all]")
        print("Or run without arguments to see this menu.\n")
        sys.exit(0)

    if choice == "all":
        for key, (desc, func) in examples.items():
            if func is not None:
                try:
                    func()
                except Exception as e:
                    print(f"Error in {desc}: {e}\n")
    elif choice in examples and examples[choice][1] is not None:
        try:
            examples[choice][1]()
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Invalid choice: {choice}")
        print("Use: python gpt5_example.py [1-5|all]")
