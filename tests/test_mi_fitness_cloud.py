from datetime import UTC, datetime

import pytest

from mi_fitness_mcp.adapters.mi_fitness_cloud import MiFitnessCloudAdapter


async def _collect(async_iterable):
    items = []
    async for item in async_iterable:
        items.append(item)
    return items


def test_optional_number_helpers():
    adapter = MiFitnessCloudAdapter(user_id="u1", pass_token="p1")
    assert adapter._optional_float(0) is None
    assert adapter._optional_float("1.5") == 1.5
    assert adapter._optional_int(0) is None
    assert adapter._optional_int("7") == 7


def test_parse_value_dict_and_json():
    adapter = MiFitnessCloudAdapter(user_id="u1", pass_token="p1")
    assert adapter._parse_value({"value": {"steps": 1}}) == {"steps": 1}
    assert adapter._parse_value({"value": '{"steps": 2}'}) == {"steps": 2}


def test_record_datetime_uses_zone_offset():
    adapter = MiFitnessCloudAdapter(user_id="u1", pass_token="p1")
    dt = adapter._record_datetime({"time": 0, "zone_offset": 10800})
    assert dt.isoformat().startswith("1970-01-01T03:00:00")


@pytest.mark.asyncio
async def test_iter_daily_activity_aggregates_steps_and_calories(monkeypatch):
    adapter = MiFitnessCloudAdapter(user_id="u1", pass_token="p1")
    adapter._connected = True
    adapter._client = object()

    async def fake_fetch(key, start_date, end_date, region=None):
        if key == "steps":
            return [
                {
                    "time": 1743467400,
                    "zone_offset": 0,
                    "value": '{"steps": 10, "distance": 8, "calories": 1}',
                },
                {
                    "time": 1743467460,
                    "zone_offset": 0,
                    "value": '{"steps": 20, "distance": 16, "calories": 2}',
                },
            ]
        if key == "calories":
            return [
                {"time": 1743467400, "zone_offset": 0, "value": '{"calories": 5}'},
                {"time": 1743467460, "zone_offset": 0, "value": '{"calories": 7}'},
            ]
        return []

    monkeypatch.setattr(adapter, "_fetch_key", fake_fetch)
    items = await _collect(adapter.iter_daily_activity("2025-04-01", "2025-04-01"))

    assert len(items) == 1
    assert items[0].steps == 30
    assert items[0].distance_m == 24
    assert items[0].active_kcal == 12


@pytest.mark.asyncio
async def test_iter_workouts_detects_sustained_intensity(monkeypatch):
    adapter = MiFitnessCloudAdapter(user_id="u1", pass_token="p1")
    adapter._connected = True
    adapter._client = object()
    start = 1_700_000_000

    async def fake_fetch(key, start_date, end_date, region=None):
        if key == "intensity":
            return [
                {"time": start + minute * 60, "zone_offset": -10800, "value": "{}"}
                for minute in range(10)
            ]
        if key == "steps":
            return [
                {
                    "time": start,
                    "value": '{"steps": 1200, "distance": 900, "calories": 60}',
                }
            ]
        if key == "calories":
            return [{"time": start, "value": '{"calories": 75}'}]
        if key == "heart_rate":
            return [
                {"time": start, "value": '{"bpm": 100}'},
                {"time": start + 60, "value": '{"bpm": 140}'},
            ]
        return []

    monkeypatch.setattr(adapter, "_fetch_key", fake_fetch)
    items = await _collect(adapter.iter_workouts("2023-11-14", "2023-11-14"))

    assert len(items) == 1
    workout = items[0]
    assert workout.activity_type == "detected_activity"
    assert workout.duration_minutes == 10
    assert workout.distance_m == 900
    assert workout.calories_kcal == 75
    assert workout.total_steps == 1200
    assert workout.avg_heart_rate_bpm == 120
    assert workout.max_heart_rate_bpm == 140
    assert workout.start_at == datetime.fromtimestamp(start - 10800, tz=UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_iter_workouts_ignores_short_intensity_bursts(monkeypatch):
    adapter = MiFitnessCloudAdapter(user_id="u1", pass_token="p1")
    adapter._connected = True
    adapter._client = object()

    async def fake_fetch(key, start_date, end_date, region=None):
        if key == "intensity":
            return [{"time": 1_700_000_000 + minute * 60, "value": "{}"} for minute in range(5)]
        raise AssertionError(f"unexpected fetch for {key}")

    monkeypatch.setattr(adapter, "_fetch_key", fake_fetch)
    items = await _collect(adapter.iter_workouts("2023-11-14", "2023-11-14"))
    assert items == []
