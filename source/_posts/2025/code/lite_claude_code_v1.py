import os
from typing import Any

import anthropic


# Get the directory where the current script is located
CWD = os.path.dirname(os.path.abspath(__file__))

# Initialize Anthropic client
client = anthropic.Anthropic(
    base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

MODEL = "claude-sonnet-4"

# System prompt for Claude Code
SYSTEM = [
    {
        "type": "text",
        "text": "You are Claude Code, Anthropic's official CLI for Claude.",
    },
    {
        "type": "text",
        "text": f"""
You are an interactive CLI tool that helps users with software engineering tasks. Use the instructions below and the tools available to you to assist the user.

Here is useful information about the environment you are running in:
<env>
Working directory: {CWD}
</env>
""",
    },
]

# Write tool definition
WRITE_TOOL = {
    "name": "Write",
    "description": "Writes a file to the local filesystem.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to write (must be absolute, not relative)",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
        },
        "required": ["file_path", "content"],
        "additionalProperties": False,
    },
}


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute tool function with user confirmation"""
    if tool_name.lower() != "write":
        return f"Error: Unknown tool `{tool_name}`"

    # User confirmation
    while True:
        file_name = os.path.basename(tool_input["file_path"])
        confirmation = (
            input(f"""
```
{tool_input["content"]}
```
Do you want to create `{file_name}`? (Y/N) > """)
            .strip()
            .lower()
        )
        if confirmation == "y":
            return write_file(tool_input["file_path"], tool_input["content"])
        else:
            return f"User rejected write to `{file_name}`"


def write_file(file_path: str, content: str) -> str:
    """Write content to a file at the specified path"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File created successfully at: {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def run_agent_in_loop(messages: list[dict], max_turns: int = 5) -> None:
    """Run the coding agent in a loop"""
    for turn in range(max_turns):
        # Call Claude
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            tools=[WRITE_TOOL],
            messages=messages,
        )

        response_content = response.content[0]

        # Text response - task completed
        if response_content.type == "text":
            print(f"\n⏺ {response_content.text}")
            break

        # Tool call
        elif response_content.type == "tool_use":
            tool_use = response_content

            # Execute tool
            tool_result = execute_tool(tool_use.name, tool_use.input)

            # Update message history
            messages.extend(
                [
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": tool_use.id,
                                "name": tool_use.name,
                                "input": tool_use.input,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": tool_result,
                            }
                        ],
                    },
                ]
            )


def main() -> None:
    """Command line interaction main function"""
    print("=" * 50)
    print("🤖 Lite Claude Code (^C to exit)")
    print("=" * 50)

    messages = []

    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue

            messages.append(
                {
                    "role": "user",
                    "content": user_input,
                }
            )
            run_agent_in_loop(messages)

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
