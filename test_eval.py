import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

def run_test():
    with TestClient(app) as client:
        print("Creating a new evaluation task...")
        task_data = {
            "question": "What is the population of France and the capital of Japan?",
            "expected_answer": "The population of France is approximately 68.4 million and the capital of Japan is Tokyo.",
            "required_tools": ["lookup_data"]
        }
        
        response = client.post("/tasks", json=task_data)
        if response.status_code == 200:
            print("Task created successfully:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Failed to create task: {response.text}")
            return
            
        print("\nTriggering evaluation (this may take a minute as the agent runs)...")
        eval_response = client.post("/evaluations/run")
        if eval_response.status_code == 200:
            print("\nEvaluation completed successfully! Results:")
            print(json.dumps(eval_response.json(), indent=2))
        else:
            print(f"Evaluation failed: {eval_response.text}")

if __name__ == "__main__":
    # We use TestClient as a context manager so it triggers the lifespan events (init_db)
    run_test()
