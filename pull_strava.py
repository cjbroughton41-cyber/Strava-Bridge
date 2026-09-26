"""
GitHub Actions Strava puller.

Runs entirely on GitHub's own servers, on a schedule - no laptop or phone
needs to be on for this to work. Fetches any new Strava activities and
commits them into activities.json (raw activity list) + state.json
(refresh token + sync cursor), which a separate Claude scheduled task reads
and pushes into the "Start Line" training app.

Requires three repo secrets: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET,
STRAVA_REFRESH_TOKEN. After the first successful run, the refresh token
that matters lives in state.json (committed to the repo) rather than the
secret, in case Strava ever rotates it.
"""
import json
import os
import datetime as dt
import requests

STATE_PATH = "state.json"
ACTIVITIES_PATH = "activities.json"
MAX_ACTIVITIES = 60  # keep the file small; oldest entries are trimmed once exceeded


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_access_token(state):
    refresh_token = state.get("refresh_token") or os.environ["STRAVA_REFRESH_TOKEN"]
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    state["refresh_token"] = data["refresh_token"]
    return data["access_token"]


def fetch_activities(token, after_epoch):
    out = []
    page = 1
    while True:
        resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={"after": after_epoch, "per_page": 100, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        out.extend(batch)
        page += 1
    return out


def main():
    state = load_json(STATE_PATH, {})
    activities = load_json(ACTIVITIES_PATH, [])
    existing_ids = {a["id"] for a in activities}

    after_epoch = state.get("last_synced_epoch")
    if after_epoch is None:
        after_epoch = int((dt.datetime.utcnow() - dt.timedelta(days=90)).timestamp())

    token = get_access_token(state)
    new = fetch_activities(token, after_epoch)

    added = 0
    newest_epoch = after_epoch
    for a in new:
        if a["id"] in existing_ids:
            continue
        activities.append({
            "id": a["id"],
            "type": a.get("type"),
            "name": a.get("name"),
            "start_date_local": a.get("start_date_local"),
            "moving_time": a.get("moving_time"),
            "distance": a.get("distance"),
            "average_heartrate": a.get("average_heartrate"),
        })
        existing_ids.add(a["id"])
        added += 1
        try:
            start_epoch = int(
                dt.datetime.fromisoformat(a["start_date_local"]).timestamp()
            )
            newest_epoch = max(newest_epoch, start_epoch)
        except (KeyError, ValueError):
            pass

    activities.sort(key=lambda a: a.get("start_date_local", ""))
    if len(activities) > MAX_ACTIVITIES:
        activities = activities[-MAX_ACTIVITIES:]

    state["last_synced_epoch"] = newest_epoch
    state["last_run_utc"] = dt.datetime.utcnow().isoformat() + "Z"

    save_json(ACTIVITIES_PATH, activities)
    save_json(STATE_PATH, state)
    print(f"Added {added} new activities. Total stored: {len(activities)}.")


if __name__ == "__main__":
    main()
