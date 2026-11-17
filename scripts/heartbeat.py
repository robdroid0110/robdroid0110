#!/usr/bin/env python3
"""Compile an image-free GitHub profile heartbeat from public GitHub events.

The output is deterministic text and a small, nonidentifying state document.
It contains no repository identifiers, commit subjects, visitor data or secrets.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / 'README.md'
STATE = ROOT / 'docs' / 'state.json'
SNAPSHOT = ROOT / 'data' / 'last_signal.json'
BEGIN = '<!-- RBD:STATE:BEGIN -->'
END = '<!-- RBD:STATE:END -->'
UTC = dt.timezone.utc


def fetch_events(user: str) -> list[dict]:
    """Retrieve only event type and timestamp; don't export repo data."""
    url = f'https://api.github.com/users/{user}/events/public?per_page=100'
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'RBD-0110-text-regenerator',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    token = os.getenv('GH_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        result = json.load(response)
    if not isinstance(result, list):
        raise ValueError('unexpected GitHub API payload')
    return result


def read_cache() -> dict:
    try:
        payload = json.loads(SNAPSHOT.read_text('utf-8'))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def phase_fraction(now: dt.datetime) -> float:
    # Reference new moon; lunar synodic period gives an illustrative estimate.
    reference = dt.datetime(2000, 1, 6, 18, 14, tzinfo=UTC)
    return ((now - reference).total_seconds() / (29.530588853 * 86400)) % 1.0


def field(seed: int) -> list[str]:
    """An eleven-line ASCII interferogram, not a contribution chart."""
    phase = (seed % 65535) / 65535 * math.tau
    glyphs = '  .:-=+*#@'
    lines = []
    for row in range(11):
        chars = []
        for col in range(29):
            x = (col - 14) / 14
            y = (row - 5) / 5
            radius = math.sqrt(x*x + y*y)
            angle = math.atan2(y, x)
            z = (math.sin(11 * radius - 4 * angle + phase)
                 + math.cos(8 * x - 5 * y + phase * 1.13)
                 + math.sin(9 * (x * y) + phase * .57)) / 3
            # Hollow center: leave a deliberate absence, not a fake meter.
            if radius < .20:
                chars.append(' ')
            else:
                idx = max(0, min(len(glyphs)-1, int((z + 1) * .5 * (len(glyphs)-1))))
                chars.append(glyphs[idx])
        lines.append(' '.join(['', ''.join(chars)]))
    return lines


def render(state: dict) -> str:
    when = state['sampled_at'].replace('T', ' ')[:16] + 'Z'
    status = state['feed_status'].upper()
    px = int(state['lunar_phase'] * 100)
    sample = state['sample_size']
    pushes = state['push_count']
    art = '\n'.join(field(state['seed']))
    return '\n'.join([
        '',
        '```text',
        '┌─ /PROC/0110 ────────────────┐',
        f'│ UTC      {when:<17}│',
        f'│ SOURCE   {status:<17}│',
        f'│ EVENTS   {str(sample):<17}│',
        f'│ PUSHES   {str(pushes):<17}│',
        f'│ LUNAR    {str(px) + "% (estimate)":<17}│',
        '└────────────────────────────┘',
        '',
        ' INTERFERENCE FIELD / SYNTHETIC',
        art,
        '',
        f' SEED   {state["seed"]:06d}',
        ' MODE   TEXT, NOT AN IMAGE',
        '```',
        '',
        '*This is a six-hour snapshot. The interference field is synthesized from a time bucket and public activity counts; it does not represent individual commits.*',
        '',
    ])


def synthesize(user: str, offline: bool = False, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(UTC)
    cache = read_cache()
    status = 'sampled'
    try:
        if offline:
            raise RuntimeError('offline mode')
        events = fetch_events(user)
        # Filter out this profile repository: prevent activity feedback loops.
        filtered = [e for e in events if
                    isinstance(e, dict) and
                    not (e.get('repo') or {}).get('name', '').endswith('/' + user) and
                    (e.get('actor') or {}).get('login', '').lower() == user.lower()]
        sample_size = len(filtered)
        push_count = sum(e.get('type') == 'PushEvent' for e in filtered)
        days = len({e.get('created_at', '')[:10] for e in filtered if e.get('created_at')})
    except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError, OSError) as exc:
        status = 'cached' if cache else 'unobserved'
        sample_size = int(cache.get('sample_size') or 0)
        push_count = int(cache.get('push_count') or 0)
        days = int(cache.get('activity_days') or 0)
        print('public event feed unavailable; using prior counts:', type(exc).__name__)
    bucket = int(now.timestamp() // (6 * 3600))
    seed_material = f'{user}:{bucket}:{sample_size}:{push_count}:{days}'
    seed = int(hashlib.sha256(seed_material.encode()).hexdigest()[:8], 16) % 1000000
    state = {
        'activity_days': days,
        'feed_status': status,
        'lunar_phase': round(phase_fraction(now), 5),
        'push_count': push_count,
        'sample_size': sample_size,
        'sampled_at': now.replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'seed': seed,
    }
    content = README.read_text('utf-8')
    if content.count(BEGIN) != 1 or content.count(END) != 1 or content.index(BEGIN) >= content.index(END):
        raise ValueError('README heartbeat markers are not intact; refusing to rewrite')
    start, tail = content.split(BEGIN, 1)
    _, end = tail.split(END, 1)
    README.write_text(start + BEGIN + '\n' + render(state) + END + end, encoding='utf-8')
    SNAPSHOT.parent.mkdir(exist_ok=True, parents=True)
    STATE.parent.mkdir(exist_ok=True, parents=True)
    state_json = json.dumps(state, indent=2, sort_keys=True) + '\n'
    SNAPSHOT.write_text(state_json, encoding='utf-8')
    STATE.write_text(state_json, encoding='utf-8')
    print('regenerated text field /', status, '/ sample=', sample_size, '/ seed=', seed)
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default='robdroid0110')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    synthesize(args.user, args.offline)
