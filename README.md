# Mi Fitness MCP

[![CI](https://github.com/kubulashvili/mi-fitness-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/kubulashvili/mi-fitness-mcp/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/kubulashvili/mi-fitness-mcp)](https://github.com/kubulashvili/mi-fitness-mcp/releases)
[![License](https://img.shields.io/github/license/kubulashvili/mi-fitness-mcp)](https://github.com/kubulashvili/mi-fitness-mcp/blob/main/LICENSE)

MCP server for Mi Fitness data.

This project provides a local SQLite-backed MCP server for Mi Fitness cloud data.

## Current data coverage

Confirmed with the current cloud flow:

- daily activity
  - steps
  - distance
  - active calories
- heart rate
- workout sessions from Xiaomi sport records
  - activity category and type
  - duration, distance, steps, and calories
  - average and maximum heart rate
  - average pace when distance is available
- body measurements
  - weight
  - BMI
  - fat, water, bone, and muscle metrics
  - visceral fat
  - basal metabolism

Not yet confirmed with the current Xiaomi cloud flow:

- sleep

### Workout detection fallback

The adapter reads explicit sport records from Xiaomi's
`data/get_sport_records_by_time` endpoint. If an account has no explicit records
for the requested range but does have minute-level intensity, steps, calories,
and heart-rate data, it groups consecutive intensity markers into sessions of
at least 10 minutes and stores them with the activity type `detected_activity`.

This deliberately does not guess whether a session was running, cycling, or
another sport. Gaps longer than two minutes split sessions, so workouts with a
pause can appear as multiple records.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Setup

You need:

- `userId`
- `passToken`

Typical flow:

1. Open `https://account.xiaomi.com`
2. Sign in to your Xiaomi account
3. Open browser DevTools
4. Inspect cookies for `account.xiaomi.com`
5. Copy `userId` and `passToken`

Configure the server:

```bash
mi-fitness-mcp setup --mode mi_fitness_cloud --user-id "<userId>" --pass-token "<passToken>" --region ru
mi-fitness-mcp doctor
```

For local endpoint exploration there is also a probe script:

```bash
python probe_mifitness.py --user-id "<userId>" --pass-token "<passToken>"
```

## Use

```bash
mi-fitness-mcp sync --start-date 2025-04-01 --end-date 2025-05-31
mi-fitness-mcp sync --type workouts --start-date 2025-04-01 --end-date 2025-05-31
mi-fitness-mcp serve
```

## MCP client config

Example `Claude Desktop` config:

```json
{
  "mcpServers": {
    "mi-fitness": {
      "command": "mi-fitness-mcp",
      "args": ["serve"]
    }
  }
}
```

## Example prompts

- `Show my daily activity for the last 14 days`
- `How has my resting heart rate changed this month?`
- `Summarize my latest body measurements`
- `Sync my latest Mi Fitness data`
- `Show my detected workouts for the last 14 days`

## Commands

```bash
mi-fitness-mcp --help
mi-fitness-mcp setup --help
mi-fitness-mcp doctor
mi-fitness-mcp sync --help
mi-fitness-mcp serve
```

## Development

```bash
pytest
python -m build
```

## Troubleshooting

- `Connection: failed`
  - verify `userId` and `passToken`
  - verify region, usually `ru`
- `Credentials not found`
  - run `setup` again
- `sync` returns no data
  - try another date range
  - verify that the data actually exists in Mi Fitness cloud

## Security

- `passToken` is stored via the system keyring
- do not commit `.env`, local config files, or real credentials
- rotate tokens if they were pasted into chats or shell history

## Disclaimer

This is an unofficial project and is not affiliated with Xiaomi.
