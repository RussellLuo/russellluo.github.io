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


class JSONLWriter:
    def __init__(self) -> None:
        # Use environment variable for output filename, default to flows.jsonl
        filename = os.getenv("MITMPROXY_OUTFILE", "flows.jsonl")
        # Open file in text mode for JSONL writing
        self.f: TextIO = open(filename, "w", encoding="utf-8")
        # Dictionary to temporarily store request data until response arrives
        self.pending_requests: Dict[str, Dict[str, Any]] = {}

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Capture request data and store temporarily until response arrives.
        Request data is stored in memory keyed by flow ID.
        """
        try:
            # Extract request information
            request_data = {
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "headers": dict(flow.request.headers),
                "timestamp": flow.request.timestamp_start,
            }

            # Add request body if it exists and is not empty
            if flow.request.content:
                try:
                    # Try to parse as JSON if content-type suggests JSON
                    content_type = flow.request.headers.get("content-type", "").lower()
                    if "application/json" in content_type:
                        request_data["body"] = flow.request.json()
                    else:
                        # For non-JSON content, store as text (decode if possible)
                        try:
                            request_data["body"] = flow.request.text
                        except UnicodeDecodeError:
                            # If can't decode as text, store as base64
                            import base64

                            request_data["body"] = base64.b64encode(
                                flow.request.content
                            ).decode("ascii")
                            request_data["body_encoding"] = "base64"
                except Exception as e:
                    # If JSON parsing fails, store as text
                    request_data["body"] = (
                        flow.request.text if flow.request.text else None
                    )
                    request_data["body_parse_error"] = str(e)

            # Store request data temporarily using flow ID as key
            self.pending_requests[flow.id] = request_data

        except Exception as e:
            # Log error but continue processing
            error_data = {
                "error": f"Failed to process request: {str(e)}",
                "url": getattr(flow.request, "pretty_url", "unknown"),
                "method": getattr(flow.request, "method", "unknown"),
                "timestamp": getattr(flow.request, "timestamp_start", None),
            }
            # Store error data temporarily as well
            self.pending_requests[flow.id] = error_data

    def response(self, flow: http.HTTPFlow) -> None:
        """
        Handle responses by combining with stored request data and writing to JSONL file.
        Each request-response pair is written as a single JSON object.
        """
        try:
            # Retrieve stored request data
            request_data = self.pending_requests.pop(flow.id, None)
            if request_data is None:
                # If no stored request data, create minimal request info
                request_data = {
                    "method": getattr(flow.request, "method", "unknown"),
                    "url": getattr(flow.request, "pretty_url", "unknown"),
                    "timestamp": getattr(flow.request, "timestamp_start", None),
                }

            # Extract response information
            response_data = {
                "status_code": flow.response.status_code,
                "reason": flow.response.reason,
                "headers": dict(flow.response.headers),
                "timestamp": flow.response.timestamp_end,
            }

            # Add response body if it exists and is not empty
            if flow.response.content:
                try:
                    # Try to parse as JSON if content-type suggests JSON
                    content_type = flow.response.headers.get("content-type", "").lower()
                    if "application/json" in content_type:
                        response_data["body"] = flow.response.json()
                    else:
                        # For non-JSON content, store as text (decode if possible)
                        try:
                            response_data["body"] = flow.response.text
                        except UnicodeDecodeError:
                            # If can't decode as text, store as base64
                            import base64

                            response_data["body"] = base64.b64encode(
                                flow.response.content
                            ).decode("ascii")
                            response_data["body_encoding"] = "base64"
                except Exception as e:
                    # If JSON parsing fails, store as text
                    response_data["body"] = (
                        flow.response.text if flow.response.text else None
                    )
                    response_data["body_parse_error"] = str(e)

            # Combine request and response data
            flow_data = {
                "request": request_data["body"],
                "response": response_data["body"],
                "flow_id": flow.id,
                "duration": (flow.response.timestamp_end or 0)
                - (flow.request.timestamp_start or 0),
            }

            # Write combined data as JSONL (one JSON object per line)
            json_line = json.dumps(flow_data, ensure_ascii=False, separators=(",", ":"))
            self.f.write(json_line + "\n")
            self.f.flush()  # Ensure data is written immediately

        except Exception as e:
            # Log error but continue processing
            error_data = {
                "error": f"Failed to process response: {str(e)}",
                "flow_id": flow.id,
                "url": getattr(flow.request, "pretty_url", "unknown"),
                "method": getattr(flow.request, "method", "unknown"),
                "timestamp": getattr(flow.response, "timestamp_end", None),
            }
            json_line = json.dumps(
                error_data, ensure_ascii=False, separators=(",", ":")
            )
            self.f.write(json_line + "\n")
            self.f.flush()

            # Clean up pending request if it exists
            self.pending_requests.pop(flow.id, None)

    def done(self):
        """Clean up resources when the addon is shutting down."""
        # Write any remaining pending requests as incomplete flows
        for flow_id, request_data in self.pending_requests.items():
            incomplete_flow = {
                "request": request_data["body"],
                "response": None,
                "flow_id": flow_id,
                "incomplete": True,
                "error": "Response not received before shutdown",
            }
            try:
                json_line = json.dumps(
                    incomplete_flow, ensure_ascii=False, separators=(",", ":")
                )
                self.f.write(json_line + "\n")
                self.f.flush()
            except Exception:
                pass  # Ignore errors during shutdown

        # Clear pending requests
        self.pending_requests.clear()

        # Close file
        if hasattr(self, "f") and not self.f.closed:
            self.f.close()


addons = [JSONLWriter()]
