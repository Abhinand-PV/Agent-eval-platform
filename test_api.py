from fastapi.testclient import TestClient
from app.main import app

def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_task_crud_and_pagination():
    with TestClient(app) as client:
        # Create Task
        payload = {
            "question": "What is 2 + 2?",
            "expected_answer": "4",
            "required_tools": ["calculate"]
        }
        res_create = client.post("/tasks", json=payload)
        assert res_create.status_code == 200
        data = res_create.json()
        assert "id" in data
        task_id = data["id"]
        assert data["question"] == payload["question"]

        # Get Single Task
        res_get = client.get(f"/tasks/{task_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == task_id

        # List Tasks with Pagination
        res_list = client.get("/tasks?limit=5&offset=0")
        assert res_list.status_code == 200
        assert isinstance(res_list.json(), list)

        # Delete Task
        res_del = client.delete(f"/tasks/{task_id}")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "success"

        # Verify Deletion (404)
        res_get_deleted = client.get(f"/tasks/{task_id}")
        assert res_get_deleted.status_code == 404


def test_agent_registration_and_pagination():
    with TestClient(app) as client:
        agent_payload = {
            "name": "Test Bot",
            "description": "Mock endpoint",
            "endpoint_url": "http://localhost:8000/mock"
        }
        res_reg = client.post("/agents", json=agent_payload)
        assert res_reg.status_code == 200
        data = res_reg.json()
        assert "id" in data

        res_list = client.get("/agents?limit=10&offset=0")
        assert res_list.status_code == 200
        assert any(a["id"] == data["id"] for a in res_list.json())


def test_evaluations_run_invalid_agent():
    with TestClient(app) as client:
        res = client.post("/evaluations/run", json={"agent_id": 999999})
        assert res.status_code == 404


def test_evaluations_summary():
    with TestClient(app) as client:
        res = client.get("/evaluations/summary")
        assert res.status_code == 200
        data = res.json()
        assert "total_evaluations" in data
        assert "avg_correctness" in data
