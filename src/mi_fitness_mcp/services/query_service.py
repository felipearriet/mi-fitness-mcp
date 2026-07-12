"""Query service for retrieving data from database."""

import json
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any

from mi_fitness_mcp.storage import Database


class QueryService:
    """Service for querying fitness data from local database."""

    def __init__(self, db: Database, user_id: str):
        """Initialize query service.

        Args:
            db: Database instance
            user_id: User identifier
        """
        self.db = db
        self.user_id = user_id

    def get_daily_summaries(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Get daily activity summaries for date range."""
        records = self.db.query_daily_activity(self.user_id, start_date, end_date)

        # Group by date and aggregate
        summaries = {}
        for record in records:
            date = record["date"]
            if date not in summaries:
                summaries[date] = {
                    "date": date,
                    "steps": 0,
                    "distance_m": 0,
                    "active_kcal": 0,
                    "total_kcal": 0,
                    "floors": 0,
                    "active_minutes": 0,
                }

            summaries[date]["steps"] += record.get("steps", 0)
            summaries[date]["distance_m"] += record.get("distance_m", 0)
            summaries[date]["active_kcal"] += record.get("active_kcal", 0)
            if record.get("total_kcal"):
                summaries[date]["total_kcal"] += record["total_kcal"]
            if record.get("floors"):
                summaries[date]["floors"] += record["floors"]
            if record.get("active_minutes"):
                summaries[date]["active_minutes"] += record["active_minutes"]

        return list(summaries.values())

    def get_metric_series(
        self,
        metric: str,
        start_date: str,
        end_date: str,
        granularity: str = "day",
        aggregation: str = "sum",
    ) -> list[dict[str, Any]]:
        """Get time series for a metric."""
        summaries = self.get_daily_summaries(start_date, end_date)

        series = []
        for summary in summaries:
            value = summary.get(metric)
            if value is not None:
                series.append(
                    {
                        "date": summary["date"],
                        "value": value,
                    }
                )

        # Apply aggregation if needed
        if granularity == "week":
            series = self._aggregate_by_week(series, aggregation)
        elif granularity == "month":
            series = self._aggregate_by_month(series, aggregation)

        return series

    def _aggregate_by_week(
        self,
        series: list[dict],
        aggregation: str,
    ) -> list[dict]:
        """Aggregate daily series by week."""
        weeks = {}

        for item in series:
            date = datetime.strptime(item["date"], "%Y-%m-%d")
            # Get week start (Monday)
            week_start = date - timedelta(days=date.weekday())
            week_key = week_start.strftime("%Y-%m-%d")

            if week_key not in weeks:
                weeks[week_key] = []
            weeks[week_key].append(item["value"])

        result = []
        for week_key, values in sorted(weeks.items()):
            if aggregation == "sum":
                value = sum(values)
            elif aggregation == "avg":
                value = sum(values) / len(values)
            elif aggregation == "min":
                value = min(values)
            elif aggregation == "max":
                value = max(values)
            else:
                value = sum(values)

            result.append({"date": week_key, "value": value})

        return result

    def _aggregate_by_month(
        self,
        series: list[dict],
        aggregation: str,
    ) -> list[dict]:
        """Aggregate daily series by month."""
        months = {}

        for item in series:
            date = datetime.strptime(item["date"], "%Y-%m-%d")
            month_key = date.strftime("%Y-%m")

            if month_key not in months:
                months[month_key] = []
            months[month_key].append(item["value"])

        result = []
        for month_key, values in sorted(months.items()):
            if aggregation == "sum":
                value = sum(values)
            elif aggregation == "avg":
                value = sum(values) / len(values)
            elif aggregation == "min":
                value = min(values)
            elif aggregation == "max":
                value = max(values)
            else:
                value = sum(values)

            result.append({"date": month_key + "-01", "value": value})

        return result

    def get_sleep_sessions(
        self,
        start_date: str,
        end_date: str,
        include_naps: bool = True,
    ) -> list[dict[str, Any]]:
        """Get sleep sessions for date range."""
        records = self.db.query_sleep_sessions(self.user_id, start_date, end_date)

        sessions = []
        for record in records:
            # Skip naps if not included
            if not include_naps and record.get("is_nap"):
                continue

            session = {
                "sleep_id": record["sleep_id"],
                "start_at": record["start_at"],
                "end_at": record["end_at"],
                "duration_minutes": record["duration_minutes"],
                "time_asleep_minutes": record["time_asleep_minutes"],
                "time_awake_minutes": record["time_awake_minutes"],
                "sleep_score": record.get("sleep_score"),
                "is_nap": record.get("is_nap", False),
            }

            # Parse stages if available
            if record.get("stages"):
                import json

                with suppress(json.JSONDecodeError):
                    session["stages"] = json.loads(record["stages"])

            sessions.append(session)

        return sessions

    def get_workouts(
        self,
        start_date: str,
        end_date: str,
        activity_types: list[str] | None = None,
        min_duration: int | None = None,
        min_distance_km: float | None = None,
    ) -> list[dict[str, Any]]:
        """Get workouts for date range with optional filters."""
        records = self.db.query_workouts(self.user_id, start_date, end_date)

        workouts = []
        for record in records:
            # Apply filters
            if activity_types and record["activity_type"].lower() not in [
                t.lower() for t in activity_types
            ]:
                continue

            if min_duration and record.get("duration_minutes", 0) < min_duration:
                continue

            if min_distance_km:
                distance_km = (record.get("distance_m") or 0) / 1000
                if distance_km < min_distance_km:
                    continue

            workouts.append(
                {
                    "workout_id": record["workout_id"],
                    "activity_type": record["activity_type"],
                    "sport_category": record.get("sport_category"),
                    "start_at": record["start_at"],
                    "end_at": record["end_at"],
                    "duration_minutes": record["duration_minutes"],
                    "distance_m": record.get("distance_m"),
                    "calories_kcal": record.get("calories_kcal"),
                    "avg_heart_rate_bpm": record.get("avg_heart_rate_bpm"),
                    "max_heart_rate_bpm": record.get("max_heart_rate_bpm"),
                    "avg_pace_sec_per_km": record.get("avg_pace_sec_per_km"),
                    "max_pace_sec_per_km": record.get("max_pace_sec_per_km"),
                    "total_steps": record.get("total_steps"),
                    "extended_metrics": (
                        json.loads(record["extended_metrics"])
                        if record.get("extended_metrics")
                        else {}
                    ),
                }
            )

        return workouts

    def summarize_workouts(
        self, start_date: str, end_date: str, group_by: str = "activity_type"
    ) -> dict[str, Any]:
        """Aggregate workout volume for a date range."""
        workouts = self.get_workouts(start_date, end_date)
        groups: dict[str, dict[str, Any]] = {}
        for workout in workouts:
            if group_by == "week":
                date = datetime.fromisoformat(str(workout["start_at"]))
                year, week, _ = date.isocalendar()
                key = f"{year}-W{week:02d}"
            else:
                key = workout["activity_type"]
            group = groups.setdefault(
                key,
                {
                    "workout_count": 0,
                    "duration_minutes": 0,
                    "distance_m": 0.0,
                    "calories_kcal": 0.0,
                },
            )
            group["workout_count"] += 1
            group["duration_minutes"] += workout["duration_minutes"] or 0
            group["distance_m"] += workout["distance_m"] or 0
            group["calories_kcal"] += workout["calories_kcal"] or 0

        totals = {
            "workout_count": len(workouts),
            "duration_minutes": sum(w["duration_minutes"] or 0 for w in workouts),
            "distance_m": sum(w["distance_m"] or 0 for w in workouts),
            "calories_kcal": sum(w["calories_kcal"] or 0 for w in workouts),
        }
        return {"start_date": start_date, "end_date": end_date, "totals": totals, "groups": groups}

    def get_workout_records(
        self,
        start_date: str,
        end_date: str,
        activity_type: str | None = None,
        group_by_activity: bool = False,
        achieved_since: str | None = None,
    ) -> dict[str, Any]:
        """Return personal best workouts, optionally separated by activity."""
        workouts = self.get_workouts(
            start_date,
            end_date,
            activity_types=[activity_type] if activity_type else None,
        )

        def calculate(items: list[dict[str, Any]], sport: str | None = None) -> dict[str, Any]:
            metrics = {
                "longest_duration": ("duration_minutes", max),
                "longest_distance": ("distance_m", max),
                "most_calories": ("calories_kcal", max),
                "highest_avg_heart_rate": ("avg_heart_rate_bpm", max),
            }
            if sport and any(token in sport for token in ("running", "walking", "hiking")):
                metrics["fastest_avg_pace"] = ("avg_pace_sec_per_km", min)

            result = {}
            for label, (field, selector) in metrics.items():
                candidates = [w for w in items if (w.get(field) or 0) > 0]
                if label == "fastest_avg_pace":
                    minimum_pace = 120 if "running" in (sport or "") else 180
                    candidates = [
                        w
                        for w in candidates
                        if w[field] >= minimum_pace
                        and (w.get("distance_m") or 0) >= 1000
                        and (w.get("duration_minutes") or 0) >= 5
                    ]
                if candidates:
                    winner = selector(candidates, key=lambda workout: workout[field])
                    result[label] = {"value": winner[field], "workout": winner}

            speed_limits = {
                "outdoor_walking": 20,
                "outdoor_hiking": 25,
                "outdoor_running": 45,
                "outdoor_riding": 120,
            }
            speed_limit = speed_limits.get(sport or "")
            speed_candidates = (
                [
                    w
                    for w in items
                    if 0 < (w.get("extended_metrics", {}).get("max_speed") or 0) <= speed_limit
                ]
                if speed_limit
                else []
            )
            if speed_candidates:
                winner = max(
                    speed_candidates,
                    key=lambda workout: workout["extended_metrics"]["max_speed"],
                )
                result["highest_max_speed"] = {
                    "value": winner["extended_metrics"]["max_speed"],
                    "workout": winner,
                }
            return result

        records = calculate(workouts, activity_type)
        response: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "records": records,
        }
        if group_by_activity:
            activities = sorted({w["activity_type"] for w in workouts})
            response["records_by_activity"] = {
                sport: calculate([w for w in workouts if w["activity_type"] == sport], sport)
                for sport in activities
            }
        if achieved_since:
            pools = response.get("records_by_activity", {"all_activities": records})
            response["new_records"] = {
                sport: {
                    label: record
                    for label, record in sport_records.items()
                    if str(record["workout"]["start_at"])[:10] >= achieved_since
                }
                for sport, sport_records in pools.items()
            }
            response["new_records"] = {
                sport: values for sport, values in response["new_records"].items() if values
            }
        return response

    def compare_workout_periods(
        self,
        first_start_date: str,
        first_end_date: str,
        second_start_date: str,
        second_end_date: str,
    ) -> dict[str, Any]:
        """Compare total workout volume between two periods."""
        first = self.summarize_workouts(first_start_date, first_end_date)["totals"]
        second = self.summarize_workouts(second_start_date, second_end_date)["totals"]
        changes = {}
        for metric in first:
            delta = second[metric] - first[metric]
            changes[metric] = {
                "absolute": delta,
                "percent": round(delta / first[metric] * 100, 1) if first[metric] else None,
            }
        return {"first_period": first, "second_period": second, "changes": changes}

    def get_body_measurements(
        self,
        start_date: str,
        end_date: str,
        metrics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get body measurements for date range."""
        records = self.db.query_body_measurements(self.user_id, start_date, end_date)

        measurements = []
        for record in records:
            measurement = {
                "timestamp": record["timestamp"],
                "weight_kg": record["weight_kg"],
            }

            # Add optional metrics
            optional_fields = [
                "bmi",
                "body_fat_pct",
                "muscle_mass_kg",
                "water_pct",
                "bone_mass_kg",
                "visceral_fat_score",
                "basal_metabolism_kcal",
                "metabolic_age",
            ]

            for field in optional_fields:
                if record.get(field) is not None:
                    measurement[field] = record[field]

            # Filter metrics if specified
            if metrics:
                filtered = {"timestamp": measurement["timestamp"]}
                for metric in metrics:
                    if metric in measurement:
                        filtered[metric] = measurement[metric]
                measurement = filtered

            measurements.append(measurement)

        return measurements

    def get_heart_rate_samples(
        self,
        start_date: str,
        end_date: str,
        sample_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        records = self.db.query_heart_rate_samples(self.user_id, start_date, end_date)

        samples = []
        for record in records:
            if sample_type and record.get("sample_type") != sample_type:
                continue
            samples.append(
                {
                    "timestamp": record["timestamp"],
                    "bpm": record["bpm"],
                    "sample_type": record.get("sample_type", "passive"),
                }
            )

        if limit is not None:
            return samples[:limit]
        return samples

    def get_data_coverage(self, data_types: list[str] | None = None) -> list[dict[str, Any]]:
        """Get data coverage information."""
        coverage = self.db.get_data_coverage(self.user_id)

        if data_types:
            coverage = [c for c in coverage if c["data_type"] in data_types]

        return coverage
