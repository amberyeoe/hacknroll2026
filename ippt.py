from datetime import date

import requests


class IPPTScoreError(Exception):
    pass


def age_on(dob, today=None):
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def fetch_ippt_score(api_url, timeout, age, situps, pushups, run_seconds):
    try:
        response = requests.get(
            api_url,
            params={
                "age": age,
                "situps": situps,
                "pushups": pushups,
                "run": run_seconds,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise IPPTScoreError(f"Unable to fetch IPPT score: {exc}") from exc
    except ValueError as exc:
        raise IPPTScoreError("IPPT API returned invalid JSON") from exc

    score = payload.get("total")
    if score is None:
        raise IPPTScoreError("IPPT API response did not include total score")

    try:
        return int(score)
    except (TypeError, ValueError) as exc:
        raise IPPTScoreError("IPPT API returned a non-numeric score") from exc
