import pytest

from mi_fitness_mcp import server


@pytest.mark.asyncio
async def test_query_workouts_tool_is_listed_and_calls_query_service(monkeypatch):
    class FakeQueryService:
        def get_workouts(self, **kwargs):
            assert kwargs == {
                "start_date": "2025-04-01",
                "end_date": "2025-04-30",
                "activity_types": ["detected_activity"],
                "min_duration": 20,
            }
            return [{"workout_id": "detected_1"}]

    monkeypatch.setattr(server, "query_service", FakeQueryService())
    tools = await server.list_tools()
    assert "query_workouts" in {tool.name for tool in tools}

    result = await server._handle_query_workouts(
        {
            "start_date": "2025-04-01",
            "end_date": "2025-04-30",
            "activity_type": "detected_activity",
            "min_duration_minutes": 20,
        }
    )
    assert result["status"] == "ok"
    assert result["data"]["count"] == 1


def test_new_workout_records_reports_changed_record_holder():
    before = {
        "outdoor_running": {"longest_distance": {"value": 5000, "workout": {"workout_id": "old"}}}
    }
    after = {
        "outdoor_running": {
            "longest_distance": {"value": 6000, "workout": {"workout_id": "new"}},
            "most_calories": {"value": 500, "workout": {"workout_id": "new"}},
        }
    }

    changed = server._new_workout_records(before, after)

    assert set(changed["outdoor_running"]) == {"longest_distance", "most_calories"}
