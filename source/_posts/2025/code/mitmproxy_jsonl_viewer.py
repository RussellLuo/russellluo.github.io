"""
Write request and response data to a JSONL file.

This script demonstrates how to capture HTTP request and response data and write them
to a JSONL (JSON Lines) file format. Each request-response pair is written as a
single JSON object on its own line, making it easy to process complete HTTP flow data.
"""

import json
import os
import re
from typing import TextIO, Dict, Any, Optional

from mitmproxy import http


def parse_sse_text(sse_string: str) -> str:
    """
    Parse Server-Sent Events (SSE) string and extract content from both text and tool use scenarios.

    This improved function processes SSE format strings and handles:
    1. Text responses: Extracts text from 'text_delta' events
    2. Tool use: Reconstructs tool calls from 'input_json_delta' events
    3. Mixed content: Handles both text and tool use in the same response

    Args:
        sse_string (str): Raw SSE string containing multiple events

    Returns:
        str: Extracted content - either text, tool use description, or both

    Example:
        >>> # Text response
        >>> sse_data = '''event: content_block_delta
        ... data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}'''
        >>> parse_sse_text(sse_data)
        'Hello'
        
        >>> # Tool use response  
        >>> sse_data = '''event: content_block_start
        ... data: {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "tool_123", "name": "search"}}
        ... event: content_block_delta
        ... data: {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{\\"query\\": \\"test\\"}"}}'''
        >>> parse_sse_text(sse_data)
        'Tool: search (ID: tool_123) - {"query": "test"}'
    """
    text_fragments = []
    tool_uses = []
    
    # Split the SSE string into individual events
    events = re.split(r"\n\nevent:", sse_string.strip())
    
    # Track tool use construction
    tool_use_data = {}  # index -> {id, name, json_fragments}
    
    for i, event in enumerate(events):
        # Add back the "event:" prefix for all but the first event
        if i > 0:
            event = "event:" + event
            
        # Skip empty events
        if not event.strip():
            continue
            
        try:
            # Extract event type and data
            lines = event.strip().split("\n")
            event_type = None
            data_json = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_json = line[5:].strip()
                    
            if not (event_type and data_json):
                continue
                
            try:
                data = json.loads(data_json)
            except json.JSONDecodeError:
                continue
                
            # Handle tool use initialization
            if event_type == "content_block_start" and isinstance(data, dict):
                content_block = data.get("content_block", {})
                if isinstance(content_block, dict) and content_block.get("type") == "tool_use":
                    index = data.get("index", 0)
                    tool_use_data[index] = {
                        "id": content_block.get("id"),
                        "name": content_block.get("name"),
                        "json_fragments": []
                    }
                    
            # Handle content deltas - both text and tool use
            elif event_type == "content_block_delta" and isinstance(data, dict):
                delta = data.get("delta", {})
                index = data.get("index", 0)
                
                if isinstance(delta, dict):
                    # Handle text deltas (normal text responses)
                    if delta.get("type") == "text_delta" and "text" in delta:
                        text_fragment = delta["text"]
                        if text_fragment:
                            text_fragments.append(text_fragment)
                            
                    # Handle input JSON deltas (tool use scenarios)
                    elif delta.get("type") == "input_json_delta" and "partial_json" in delta:
                        partial_json = delta["partial_json"]
                        if index in tool_use_data and partial_json:
                            tool_use_data[index]["json_fragments"].append(partial_json)
                            
            # Handle tool use finalization
            elif event_type == "content_block_stop" and isinstance(data, dict):
                index = data.get("index", 0)
                if index in tool_use_data:
                    tool_data = tool_use_data[index]
                    json_string = "".join(tool_data["json_fragments"])
                    
                    try:
                        parsed_input = json.loads(json_string) if json_string.strip() else {}
                        tool_uses.append({
                            "id": tool_data["id"],
                            "name": tool_data["name"],
                            "input": parsed_input
                        })
                    except json.JSONDecodeError:
                        # Try to extract readable information from the malformed JSON
                        readable_content = json_string.strip()
                        if readable_content:
                            # Try to extract key-value pairs even if JSON is malformed
                            # Look for patterns like "key": "value" or "key": value
                            pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', readable_content)
                            if pairs:
                                simplified_input = {key: value for key, value in pairs}
                                tool_uses.append({
                                    "id": tool_data["id"],
                                    "name": tool_data["name"],
                                    "input": simplified_input
                                })
                            else:
                                # Fallback to showing the raw content
                                tool_uses.append({
                                    "id": tool_data["id"],
                                    "name": tool_data["name"],
                                    "input": readable_content,
                                })
                        else:
                            # Empty input
                            tool_uses.append({
                                "id": tool_data["id"],
                                "name": tool_data["name"],
                                "input": {}
                            })
                        
        except Exception:
            # Skip malformed events
            continue
            
    # Build result string
    result_parts = []
    
    # Add text content if any
    if text_fragments:
        result_parts.append("".join(text_fragments))
        
    # Add tool use descriptions if any
    if tool_uses:
        for tool_use in tool_uses:
            tool_desc = f"Tool: {tool_use['name']} (ID: {tool_use['id']})"
            if isinstance(tool_use['input'], dict) and tool_use['input']:
                input_summary = json.dumps(tool_use['input'], ensure_ascii=False)
                tool_desc += f" - {input_summary}"
            elif tool_use['input']:
                tool_desc += f" - {tool_use['input']}"
            result_parts.append(tool_desc)
            
    return " | ".join(result_parts) if result_parts else ""


def parse_sse_events(sse_string: str) -> Dict[str, Any]:
    """
    Parse Server-Sent Events (SSE) string and return structured event data.

    This enhanced function provides detailed parsing of SSE strings, handling both
    text responses and tool use scenarios, returning all events with their types
    and data for comprehensive analysis.

    Args:
        sse_string (str): Raw SSE string containing multiple events

    Returns:
        Dict[str, Any]: Dictionary containing parsed events, extracted text, and tool use info

    Example:
        >>> result = parse_sse_events(sse_data)
        >>> result['text']  # Concatenated text content
        >>> result['events']  # List of all parsed events
        >>> result['message_id']  # Message ID if available
        >>> result['tool_uses']  # List of reconstructed tool uses
        >>> result['tool_use_count']  # Number of tool uses found
    """
    events = []
    text_fragments = []
    tool_uses = []
    message_id = None
    model = None
    usage_info = None
    
    # Track tool use construction
    tool_use_data = {}  # index -> {id, name, json_fragments}

    # Split the SSE string into individual events
    event_blocks = re.split(r"\n\nevent:", sse_string.strip())

    for i, event_block in enumerate(event_blocks):
        # Add back the "event:" prefix for all but the first event
        if i > 0:
            event_block = "event:" + event_block

        # Skip empty events
        if not event_block.strip():
            continue

        try:
            # Extract event type and data
            lines = event_block.strip().split("\n")
            event_type = None
            data_json = None

            for line in lines:
                line = line.strip()
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_json = line[5:].strip()

            if event_type and data_json:
                try:
                    # Parse the JSON data
                    data = json.loads(data_json)

                    # Store the parsed event
                    events.append({"type": event_type, "data": data})

                    # Extract specific information based on event type
                    if event_type == "message_start" and isinstance(data, dict):
                        message_info = data.get("message", {})
                        if isinstance(message_info, dict):
                            message_id = message_info.get("id")
                            model = message_info.get("model")
                            
                    elif event_type == "content_block_start" and isinstance(data, dict):
                        # Initialize tool use tracking
                        content_block = data.get("content_block", {})
                        if isinstance(content_block, dict) and content_block.get("type") == "tool_use":
                            index = data.get("index", 0)
                            tool_use_data[index] = {
                                "id": content_block.get("id"),
                                "name": content_block.get("name"),
                                "json_fragments": []
                            }

                    elif event_type == "content_block_delta" and isinstance(data, dict):
                        delta = data.get("delta", {})
                        index = data.get("index", 0)
                        
                        if isinstance(delta, dict):
                            # Extract text from text deltas
                            if delta.get("type") == "text_delta" and "text" in delta:
                                text_fragment = delta["text"]
                                if text_fragment:
                                    text_fragments.append(text_fragment)
                                    
                            # Extract JSON from input deltas (tool use)
                            elif delta.get("type") == "input_json_delta" and "partial_json" in delta:
                                partial_json = delta["partial_json"]
                                if index in tool_use_data and partial_json:
                                    tool_use_data[index]["json_fragments"].append(partial_json)
                                    
                    elif event_type == "content_block_stop" and isinstance(data, dict):
                        # Finalize tool use construction
                        index = data.get("index", 0)
                        if index in tool_use_data:
                            tool_data = tool_use_data[index]
                            json_string = "".join(tool_data["json_fragments"])
                            
                            try:
                                parsed_input = json.loads(json_string) if json_string.strip() else {}
                                tool_uses.append({
                                    "id": tool_data["id"],
                                    "name": tool_data["name"],
                                    "input": parsed_input
                                })
                            except json.JSONDecodeError:
                                # Try to extract readable information from the malformed JSON
                                readable_content = json_string.strip()
                                if readable_content:
                                    # Try to extract key-value pairs even if JSON is malformed
                                    # Look for patterns like "key": "value" or "key": value
                                    pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', readable_content)
                                    if pairs:
                                        simplified_input = {key: value for key, value in pairs}
                                        tool_uses.append({
                                            "id": tool_data["id"],
                                            "name": tool_data["name"],
                                            "input": simplified_input
                                        })
                                    else:
                                        # Fallback to showing the raw content
                                        tool_uses.append({
                                            "id": tool_data["id"],
                                            "name": tool_data["name"],
                                            "input": readable_content if len(readable_content) <= 100 else readable_content[:97] + "...",
                                            "parse_error": True
                                        })
                                else:
                                    # Empty input
                                    tool_uses.append({
                                        "id": tool_data["id"],
                                        "name": tool_data["name"],
                                        "input": {}
                                    })

                    elif event_type == "message_delta" and isinstance(data, dict):
                        # Extract usage information
                        usage_info = data.get("usage")

                except json.JSONDecodeError:
                    # Store unparseable events as raw data
                    events.append(
                        {"type": event_type, "data": data_json, "parse_error": True}
                    )

        except Exception as e:
            # Store malformed events with error info
            events.append(
                {"type": "parse_error", "raw_data": event_block, "error": str(e)}
            )

    return {
        "text": "".join(text_fragments),
        "events": events,
        "message_id": message_id,
        "model": model,
        "usage": usage_info,
        "event_count": len(events),
        "text_fragment_count": len(text_fragments),
        "tool_uses": tool_uses,
        "tool_use_count": len(tool_uses),
    }


def iterate_flows_jsonl(input_stream: TextIO):
    """
    Generator function to iterate through each JSON line from an input stream.

    This function yields each parsed JSON object from the flows.jsonl content,
    allowing for memory-efficient processing of large files or stdin input.

    Args:
        input_stream (TextIO): Input stream to read from (required).

    Yields:
        Dict[str, Any]: Parsed JSON object for each flow

    Example:
        >>> # Read from stdin
        >>> import sys
        >>> for flow in iterate_flows_jsonl(sys.stdin):
        ...     print(f"Processing flow {flow['flow_id']}")
        ...     # Process individual flow data
        ...     if 'error' in flow.get('response', {}):
        ...         print(f"Flow had error: {flow['response']['error']['message']}")
        
        >>> # Read from file
        >>> with open('flows.jsonl', 'r') as f:
        ...     for flow in iterate_flows_jsonl(f):
        ...         print(f"Processing flow {flow['flow_id']}")
    """
    import sys
    
    try:
        line_number = 0
        for line in input_stream:
            line_number += 1
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            try:
                # Parse and yield JSON line
                flow_data = json.loads(line)
                yield flow_data

            except json.JSONDecodeError as e:
                print(f"Warning: Error parsing JSON on line {line_number}: {e}", file=sys.stderr)
                continue

    except Exception as e:
        print(f"Error reading input stream: {e}", file=sys.stderr)
        return


def show_flows(input_stream: TextIO):
    """
    Display simplified information for each flow, showing only system and messages for requests,
    and parsed SSE text for responses.

    This function iterates through all flows from the input stream and prints:
    - Request: Only 'system' and 'messages' parts from the request body
    - Response: Parsed text using parse_sse_text if response is string, otherwise error message
    
    Args:
        input_stream (TextIO): Input stream to read from (required).
    """
    flow_count = 0

    for flow in iterate_flows_jsonl(input_stream):
        flow_count += 1
        flow_id = flow.get("flow_id", "Unknown")
        timestamp = flow.get("timestamp", "Unknown")

        print("=" * 80)
        print(f"FLOW #{flow_count} - ID: {flow_id}")
        print(f"Timestamp: {timestamp}")
        print("=" * 80)

        # Display Request Information - Only system and messages
        print("\n📤 REQUEST:")
        print("-" * 40)

        request = flow.get("request", {})
        if request:
            body = request
            if body:
                try:
                    # Try to parse request body as JSON
                    request_data = body

                    # Display system part if present
                    if "system" in request_data:
                        print("System:")
                        system_content = request_data["system"]
                        if isinstance(system_content, list):
                            for i, message in enumerate(system_content):
                                print(f"  System[{i}]:")
                                if isinstance(message, dict):
                                    for key, value in message.items():
                                        print(f"    {key}: {value}")
                                else:
                                    print(f"    {message}")
                        elif isinstance(system_content, dict):
                            print(f"  System:")
                            for key, value in system_content.items():
                                print(f"    {key}: {value}")
                        else:
                            print(
                                f"  {json.dumps(system_content, indent=2, ensure_ascii=False)}"
                            )

                    # Display messages part if present
                    if "messages" in request_data:
                        print("Messages:")
                        messages = request_data["messages"]
                        if isinstance(messages, list):
                            for i, message in enumerate(messages):
                                print(f"  Message[{i}]:")
                                if isinstance(message, dict):
                                    # Display non-content fields first
                                    for key, value in message.items():
                                        if key != "content":
                                            print(f"    {key}: {value}")
                                    
                                    # Handle content array specially
                                    if "content" in message:
                                        content = message["content"]
                                        if isinstance(content, list):
                                            print(f"    content:")
                                            for j, content_item in enumerate(content):
                                                print(f"      Content[{j}]:")
                                                if isinstance(content_item, dict):
                                                    # Display non-text fields first
                                                    for key, value in content_item.items():
                                                        if key != "text":
                                                            print(f"        {key}: {value}")
                                                    
                                                    # Expand and display text content if it's a text type
                                                    if content_item.get("type") == "text" and "text" in content_item:
                                                        text_content = content_item["text"]
                                                        print(f"        text:")
                                                        # Split text into lines and indent each line
                                                        if isinstance(text_content, str):
                                                            text_lines = text_content.split('\n')
                                                            for line in text_lines:
                                                                print(f"          {line}")
                                                        else:
                                                            print(f"          {text_content}")
                                                else:
                                                    print(f"        {content_item}")
                                        else:
                                            print(f"    content: {content}")
                                else:
                                    print(f"    {message}")
                        else:
                            print(
                                f"  {json.dumps(messages, indent=2, ensure_ascii=False)}"
                            )

                    # Display tools part if present
                    if "tools" in request_data:
                        print("Tools:")
                        tools = request_data["tools"]
                        if isinstance(tools, list):
                            for i, tool in enumerate(tools):
                                print(f"  Tool[{i}]:")
                                if isinstance(tool, dict):
                                    # Display tool name
                                    if "name" in tool:
                                        print(f"    Name: {tool['name']}")
                                    
                                    # Display tool description
                                    if "description" in tool:
                                        description = tool["description"]
                                        # Truncate long descriptions for readability
                                        print(f"    Description: {description}")
                                    
                                    # Display input schema summary
                                    if "input_schema" in tool:
                                        schema = tool["input_schema"]
                                        if isinstance(schema, dict):
                                            print(f"    Input Schema:")
                                            # Show schema type
                                            if "type" in schema:
                                                print(f"      Type: {schema['type']}")
                                            
                                            # Show required properties
                                            if "required" in schema and isinstance(schema["required"], list):
                                                print(f"      Required: {', '.join(schema['required'])}")
                                            
                                            # Show properties summary
                                            if "properties" in schema and isinstance(schema["properties"], dict):
                                                prop_count = len(schema["properties"])
                                                prop_names = list(schema["properties"].keys())
                                                if prop_count <= 5:
                                                    print(f"      Properties: {', '.join(prop_names)}")
                                                else:
                                                    print(f"      Properties ({prop_count}): {', '.join(prop_names[:5])}...")
                                        else:
                                            print(f"    Input Schema: {str(schema)[:100]}...")
                                    
                                    print()  # Add blank line between tools
                                else:
                                    print(f"    {tool}")
                        else:
                            print(f"  {json.dumps(tools, indent=2, ensure_ascii=False)}")

                    # Show warning if none of the expected fields are found
                    if not any(key in request_data for key in ["system", "messages", "tools"]):
                        print("No 'system', 'messages', or 'tools' found in request body")

                except json.JSONDecodeError:
                    print(
                        "Request body is not valid JSON - cannot extract system/messages"
                    )
            else:
                print("No request body available")
        else:
            print("No request data available")

        # Display Response Information - Parse SSE text or show error
        print("\n📥 RESPONSE:")
        print("-" * 40)

        response = flow.get("response", {})
        if response:
            # Check for error responses first
            if "error" in response:
                error_info = response["error"]
                print(f"❌ ERROR RESPONSE")
                print(f"Error Message: {error_info.get('message', 'Unknown error')}")
            else:
                body = response

                if body:
                    # Check if response body is a string
                    if isinstance(body, str):
                        try:
                            # Use parse_sse_text to extract content
                            parsed_text = parse_sse_text(body)
                            if parsed_text:
                                print("📡 Parsed SSE Response:")
                                print(f"  {parsed_text}")
                            else:
                                print("📡 SSE Response (no text content extracted):")
                                print(f"  Raw content preview: {body[:200]}...")
                        except Exception as e:
                            print(f"❌ Error parsing SSE response: {e}")
                            print(f"  Raw content preview: {body[:200]}...")
                    else:
                        print("❌ Error: Response body is not a string")
                        print(f"  Response body type: {type(body).__name__}")
                        print(f"  Response body content: {str(body)[:200]}...")
                else:
                    print("No response body available")
        else:
            print("No response data available")

        print("\n" + "=" * 80 + "\n")

    print(f"📊 SUMMARY: Processed {flow_count} flows total")


if __name__ == "__main__":
    import sys
    
    # Check if there are command line arguments for file input
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                show_flows(file)
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{file_path}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin by default
        show_flows(sys.stdin)
