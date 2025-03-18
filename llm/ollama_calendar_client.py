import requests
import json
import re
import subprocess
import time
import os

MODEL = "llama3"  # or another model you have pulled
MCP_SERVER_PATH = (
    "/Users/naeemujeeb/Downloads/google-calendar-mcp"  # Path to your MCP server
)


class CalendarClient:
    def __init__(self):
        self.server_process = self.start_mcp_server()
        time.sleep(2)  # Wait for server to start

        self.setup_communication()

        self.context = None

        print(f"Calendar client initialized with {MODEL} model")

    def start_mcp_server(self):
        """Start the Google Calendar MCP server"""
        print("Starting Google Calendar MCP server...")
        process = subprocess.Popen(
            ["npm", "start"],
            cwd=MCP_SERVER_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return process

    def setup_communication(self):
        """Set up communication with the MCP server"""
        # In a real implementation, this would establish proper MCP protocol communication
        # For now, we'll use a simplified approach
        self.next_request_id = 1

    def query_ollama(self, prompt, system=""):
        """Send a query to Ollama and get the response"""
        payload = {"model": MODEL, "prompt": prompt, "system": system, "stream": False}

        if self.context:
            payload["context"] = self.context

        print(f"Sending request to Ollama API...")
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=30,  # Add a timeout
            )
            print(f"Received response with status code: {response.status_code}")

            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return f"Error communicating with Ollama: {response.status_code}"

            result = response.json()
            self.context = result.get("context", None)
            return result.get("response", "")
        except requests.exceptions.Timeout:
            print("Request to Ollama timed out after 30 seconds")
            return "Request to AI model timed out. Please try again."
        except requests.exceptions.ConnectionError:
            print("Connection error when contacting Ollama API")
            return "Could not connect to AI model. Is Ollama running?"
        except json.JSONDecodeError:
            print(f"Invalid JSON response from Ollama: {response.text[:100]}...")
            return "Received invalid response from AI model."
        except Exception as e:
            print(f"Unexpected error querying Ollama: {str(e)}")
            return f"Error: {str(e)}"

    def extract_tool_calls(self, text):
        """Extract tool calls from the model's response"""
        # Look for JSON blocks in the response
        pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = re.findall(pattern, text, re.DOTALL)

        tool_calls = []
        for match in matches:
            try:
                data = json.loads(match)
                if "name" in data and "args" in data:
                    tool_calls.append(data)
            except json.JSONDecodeError:
                print(f"Failed to parse tool call: {match}")

        return tool_calls

    def execute_tool(self, tool_name, args):
        """Execute a tool call against the MCP server"""
        # This is a simplified implementation that doesn't use the actual MCP protocol
        # In a real implementation, you would send proper MCP requests
        if tool_name == "list-events" and "calendarId" not in args:
            args["calendarId"] = "kdenaeexm@gmail.com"

        # Similarly for other tools
        if tool_name == "create-event" and "calendarId" not in args:
            args["calendarId"] = "kdenaeexm@gmail.com"

        if tool_name == "update-event" and "calendarId" not in args:
            args["calendarId"] = "primary"

        if tool_name == "delete-event" and "calendarId" not in args:
            args["calendarId"] = "primary"

        if tool_name == "list-calendars":
            return "Primary Calendar (primary)\nWork Calendar (work@example.com)\nFamily Calendar (family@example.com)"

        elif tool_name == "list-events":
            calendar_id = args.get("calendarId", "primary")
            return f"Events for {calendar_id}:\n1. Team Meeting (9:00 AM - 10:00 AM)\n2. Lunch with Sarah (12:00 PM - 1:00 PM)\n3. Project Review (3:00 PM - 4:00 PM)"

        elif tool_name == "create-event":
            summary = args.get("summary", "Untitled Event")
            start = args.get("start", "Unknown time")
            end = args.get("end", "Unknown time")
            return f"Created event: {summary} from {start} to {end}"

        elif tool_name == "update-event":
            event_id = args.get("eventId", "unknown")
            changes = ", ".join(
                [
                    f"{k}: {v}"
                    for k, v in args.items()
                    if k not in ["calendarId", "eventId"]
                ]
            )
            return f"Updated event {event_id} with changes: {changes}"

        elif tool_name == "delete-event":
            event_id = args.get("eventId", "unknown")
            return f"Deleted event: {event_id}"

        return f"Unknown tool: {tool_name}"

    def run_interactive(self):
        """Run an interactive session with the user"""
        print("Running AI Agent session. Type 'exit' to quit.")
        system_prompt = """You are a helpful assistant that can manage Google Calendar.
                    You have access to these tools:
                    - list-calendars: Lists all available calendars
                    - list-events: Lists events from a calendar (requires calendarId)
                    - create-event: Creates a new event (requires calendarId, summary, start, end)
                    - update-event: Updates an event (requires calendarId, eventId)
                    - delete-event: Deletes an event (requires calendarId, eventId)

                    When you need to use a tool, respond with a JSON object in this format:
                    ```json
                    {
                      "name": "tool-name",
                      "args": {
                        "param1": "value1",
                        "param2": "value2"
                      }
                    }
                    After using tools, provide a helpful, concise response to the user's query.
                    """
        try:
            while True:
                user_input = input("\n0: ")
                if user_input.lower() in ["exit", "quit", "bye"]:
                    break

                # Get initial response from model
                response = self.query_ollama(user_input, system_prompt)
                tool_calls = self.extract_tool_calls(response)

                if tool_calls:
                    print("\nAssistant is using tools to help you...")

                    # Execute each tool call
                    results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        args = tool_call["args"]

                        print(f"\nExecuting: {tool_name}")
                        print(f"Arguments: {json.dumps(args, indent=2)}")

                        result = self.execute_tool(tool_name, args)
                        print(f"Result: {result}")
                        results.append(f"Result of {tool_name}: {result}")

                    # Format results for follow-up
                    all_results = "\n".join(results)
                    follow_up_prompt = f"{user_input}\n\nTool results:\n{all_results}"

                    # Get final response with results
                    final_response = self.query_ollama(follow_up_prompt, system_prompt)

                    # Clean up the response by removing tool call syntax
                    cleaned_response = re.sub(
                        r"```json\s*\{.*?\}\s*```",
                        "",
                        final_response,
                        flags=re.DOTALL,
                    )
                    cleaned_response = cleaned_response.strip()

                    print("\nAssistant:", cleaned_response)
                else:
                    print("\nAssistant:", response)

        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Shutting down...")
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)


if __name__ == "__main__":
    print("running")
    client = CalendarClient()
    client.run_interactive()
