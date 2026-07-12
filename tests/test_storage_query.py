from datetime import datetime

from mi_fitness_mcp.models import BodyMeasurement, DailyActivity, HeartRateSample, Workout
from mi_fitness_mcp.services.query_service import QueryService
from mi_fitness_mcp.storage import Database


def test_storage_and_query_roundtrip(tmp_path):
    db = Database(tmp_path / "test.db")

    activity = DailyActivity(
        id="a1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        date="2025-04-01",
        steps=1000,
        distance_m=800,
        active_kcal=50,
    )
    hr = HeartRateSample(
        id="hr1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        timestamp=datetime(2025, 4, 1, 12, 0, 0),
        bpm=70,
        sample_type="passive",
    )
    body = BodyMeasurement(
        id="w1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        timestamp=datetime(2025, 4, 1, 7, 0, 0),
        weight_kg=101.5,
        bmi=28.0,
    )
    workout = Workout(
        id="wo1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        workout_id="detected_1",
        activity_type="detected_activity",
        sport_category="walking",
        start_at=datetime(2025, 4, 1, 12, 0, 0),
        end_at=datetime(2025, 4, 1, 12, 30, 0),
        duration_minutes=30,
        distance_m=3000,
        calories_kcal=200,
        extended_metrics={"train_effect": 2.0},
        raw_payload={"sport_type": 2},
    )

    db.insert_daily_activity(activity)
    db.insert_heart_rate_sample(hr)
    db.insert_body_measurement(body)
    db.insert_workout(workout)

    query = QueryService(db, "u1")
    assert len(query.get_daily_summaries("2025-04-01", "2025-04-01")) == 1
    assert len(query.get_heart_rate_samples("2025-04-01", "2025-04-01")) == 1
    assert len(query.get_body_measurements("2025-04-01", "2025-04-01")) == 1
    workouts = query.get_workouts("2025-04-01", "2025-04-01")
    assert len(workouts) == 1
    assert workouts[0]["sport_category"] == "walking"
    assert workouts[0]["extended_metrics"]["train_effect"] == 2.0
    assert db.delete_detected_workouts("u1", "2025-04-01", "2025-04-01") == 1
    assert query.get_workouts("2025-04-01", "2025-04-01") == []
