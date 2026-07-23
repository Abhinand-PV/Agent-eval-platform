from langchain_core.tools import tool


@tool
def lookup_data(query: str) -> str:
    """Look up factual data for a given query. Returns relevant information."""
    # Simulated data store with canned responses
    data_store = {
        "population of france": "The population of France is approximately 68.4 million as of 2024.",
        "capital of japan": "The capital of Japan is Tokyo.",
        "speed of light": "The speed of light in vacuum is 299,792,458 meters per second.",
        "python creator": "Python was created by Guido van Rossum and first released in 1991.",
    }
    # Normalize the query and check for partial matches
    key = query.lower().strip()
    for k, v in data_store.items():
        if k in key or key in k:
            return v
    return f"No data found for: {query}"
@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result."""
    try:
        # Only allow safe characters for evaluation
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {e}"