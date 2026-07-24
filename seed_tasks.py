import asyncio

from app.database import async_session, init_db
from app.models import EvalTask

async def seed():
    await init_db()
    async with async_session() as session:
        tasks = [
            EvalTask(
                question="What is the population of France?",
                expected_answer="The population of France is approximately 68.4 million.",
                required_tools=["lookup_data"],
            ),
            EvalTask(
                question="What is 245 * 18?",
                expected_answer="4410",
                required_tools=["calculate"],
            ),
            EvalTask(
                question="What is the meaning of life according to Douglas Adams?",
                expected_answer="42",
                required_tools=[],
            ),
        ]
        session.add_all(tasks)
        await session.commit()
        print(f"Seeded {len(tasks)} evaluation tasks.")

if __name__ == "__main__":
    asyncio.run(seed())