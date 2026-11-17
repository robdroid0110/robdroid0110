#!/usr/bin/env python3
"""Reconstitute a GitHub-safe, self-contained SVG without third-party dependencies.

Source: GitHub public events only. Exports aggregates, never repository names.
The lunar model is approximate and computed offline; updates are periodic, not live.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import math
from pathlib import Path
import random
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'assets' / 'organism.svg'
CACHE = ROOT / 'data' / 'last_signal.json'
SYNODIC_MONTH = 29.530588853
# Approximate epoch for a new moon, not an astronomical ephemeris.
NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
UTC = timezone.utc


def iso_date(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_cached_sample() -> dict | None:
    if not CACHE.exists():
        return None
    try:
        cache = json.loads(CACHE.read_text(encoding='utf-8'))
        if isinstance(cache.get('push_count'), int) and isinstance(cache.get('activity_days'), int):
            return cache
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return None


def get_public_signal(user: str, now: datetime) -> dict:
    """Sample up to 300 of the newest public events (not lifetime contributions)."""
    token = __import__('os').environ.get('GH_TOKEN', '')
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'robdroid0110-profile-organism/1.0',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'

    events: list[dict] = []
    # A hard cap is important: the public events feed has a limited history.
    for page in (1, 2, 3):
        url = f'https://api.github.com/users/{user}/events/public?per_page=100&page={page}'
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
        if not isinstance(payload, list):
            raise ValueError('Unexpected public event response')
        events.extend(x for x in payload if isinstance(x, dict))
        if len(payload) < 100:
            break

    cutoff = now - timedelta(days=90)
    push_times: list[datetime] = []
    for event in events:
        if event.get('type') != 'PushEvent':
            continue
        try:
            when = datetime.fromisoformat(str(event['created_at']).replace('Z', '+00:00'))
        except (ValueError, KeyError):
            continue
        if cutoff <= when <= now:
            push_times.append(when)
    push_times.sort()
    sample = {
        'push_count': len(push_times),
        'activity_days': len({p.date().isoformat() for p in push_times}),
        'latest_push': iso_date(push_times[-1]) if push_times else None,
        'sample_size': len(events),
        'sampled_at': iso_date(now),
    }
    return sample


def moon_illumination(now: datetime) -> tuple[float, float]:
    days = (now - NEW_MOON_EPOCH).total_seconds() / 86400.0
    phase = (days / SYNODIC_MONTH) % 1.0
    illumination = (1.0 - math.cos(2.0 * math.pi * phase)) / 2.0
    return phase, illumination


def f(num: float) -> str:
    return f'{num:.2f}'


def path(points: list[tuple[float, float]]) -> str:
    return 'M ' + ' L '.join(f'{f(x)} {f(y)}' for x, y in points)


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def node(x: float, y: float, radius: float, color: str, alpha: float = 1.0) -> str:
    return (f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(radius)}" '
            f'fill="{color}" opacity="{f(alpha)}"/>')


def text(x: float, y: float, content: str, size: int, color: str,
         weight: int = 400, letter: int = 0, family: str = 'mono', extra: str = '') -> str:
    fonts = {
        'mono': "'DejaVu Sans Mono','Consolas',monospace",
        'sans': "'DejaVu Sans','Arial',sans-serif",
    }
    return (f'<text x="{x}" y="{y}" font-size="{size}" '
            f'font-family="{fonts[family]}" font-weight="{weight}" '
            f'letter-spacing="{letter}" fill="{color}" {extra}>{esc(content)}</text>')


def render(now: datetime, sample: dict, state: str, user: str) -> str:
    phase, illumination = moon_illumination(now)
    bucket = int(now.timestamp()) // (6 * 3600)
    digest = hashlib.sha256(
        f'{user}|{bucket}|{sample["push_count"]}|{sample["activity_days"]}|{phase:.5f}'.encode()
    ).hexdigest()
    rng = random.Random(int(digest[:16], 16))

    ink = '#080e12'
    white = '#f1f3e6'
    dim = '#90a39c'
    neon = '#c2ff57'
    cyan = '#6fe1d8'
    rust = '#ff775c'
    lines: list[str] = []
    a = lines.append
    a('<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="820" '
      'viewBox="0 0 1400 820" role="img" aria-labelledby="title desc">')
    a('<title id="title">RBD-0110 — Untrusted Organism</title>')
    a('<desc id="desc">An algorithmic alien specimen: unique generative filaments are computed '
      'from sampled public GitHub push events and an approximate lunar cycle. '
      'No project names or private data are displayed.</desc>')
    a('''<defs>
      <radialGradient id="back" cx="73%" cy="48%" r="65%"><stop stop-color="#162728"/>
        <stop offset="0.55" stop-color="#0b1417"/><stop offset="1" stop-color="#05090d"/></radialGradient>
      <radialGradient id="membrane"><stop stop-color="#234a3e" stop-opacity=".72"/>
        <stop offset=".58" stop-color="#153c36" stop-opacity=".45"/>
        <stop offset="1" stop-color="#72b77c" stop-opacity=".015"/></radialGradient>
      <radialGradient id="core"><stop stop-color="#f4ffe1"/><stop offset=".12" stop-color="#bafc69"/>
        <stop offset=".35" stop-color="#356e52"/><stop offset="1" stop-color="#0c1819"/></radialGradient>
      <filter id="aura" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="9"/></filter>
      <pattern id="dotfield" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r=".7" fill="#637b73" opacity=".18"/>
      </pattern>
      <clipPath id="frame"><rect x="3" y="3" width="1394" height="814"/></clipPath>
    </defs>''')
    a('<g clip-path="url(#frame)">')
    a('<rect width="1400" height="820" fill="url(#back)"/>')
    a('<rect width="1400" height="820" fill="url(#dotfield)"/>')

    # Brutalist cuts and registration marks; nothing resembling UI cards.
    a('<path d="M 31 42 H 500 M 31 42 V 786 M 1367 42 H 1195 M 1367 42 V 786 '
      'M 31 786 H 1367" fill="none" stroke="#395750" stroke-width="1.5"/>')
    a('<path d="M 31 120 H 1367 M 31 692 H 1367" fill="none" stroke="#3d5a50" stroke-width="1" opacity=".7"/>')
    a('<path d="M 660 120 V 692" fill="none" stroke="#314c44" stroke-width="1" stroke-dasharray="3 11"/>')
    a('<path d="M 31 42 H 178" fill="none" stroke="#c2ff57" stroke-width="4"/>')
    a('<path d="M 1220 786 H 1367" fill="none" stroke="#ff775c" stroke-width="4"/>')
    a(text(75, 89, 'RBD-0110 // AUTOGENETIC DOCUMENT', 17, neon, 700, 2))
    a(text(1324, 89, 'READ ONLY  /  2042', 15, dim, 400, 1, extra='text-anchor="end"'))
    # Dense editorial typography rather than a conventional profile introduction.
    a(text(72, 224, 'UNTRUSTED', 84, white, 800, -3, 'sans'))
    a(text(72, 315, 'ORGANISM', 84, white, 800, -3, 'sans'))
    a('<rect x="76" y="341" width="138" height="7" fill="#c2ff57"/>')
    a(text(75, 400, 'DEAD_DROID', 24, neon, 700, 2))
    a(text(75, 437, 'ARCH / ANDROID / SHELL / NETWORKS', 16, dim, 400, 1))
    a(text(75, 532, 'NOTHING IS A BLACK BOX.', 25, white, 700, 0, 'sans'))
    a(text(75, 564, 'IT IS MERELY UNOPENED.', 25, white, 700, 0, 'sans'))
    a(text(75, 634, 'DISASSEMBLE THE ASSUMPTION.', 14, cyan, 400, 2))
    a(text(75, 659, 'REWRITE THE BOUNDARY.', 14, cyan, 400, 2))

    # The nucleus is an organic field, not a widget. Lunar phase alters the membrane.
    cx, cy = 1010.0, 400.0
    shifted = phase * math.tau
    pulse = min(sample['push_count'], 60) / 60.0
    rbase = 194 + 20 * illumination + 10 * pulse
    a(node(cx, cy, 228, neon, .045).replace('/>', ' filter="url(#aura)"/>'))

    for ring in range(7):
        r = 98 + ring * 33
        points = []
        for i in range(181):
            theta = (i / 180.0) * math.tau
            warp = (5 + ring * 1.9) * math.sin(7 * theta + shifted + ring*.31)
            warp += (2.3 + ring*.65)*math.sin(13*theta - shifted*.7)
            rr = r + warp
            points.append((cx + rr*math.cos(theta), cy + rr*math.sin(theta)))
        a(f'<path d="{path(points)}" fill="none" stroke="{cyan if ring%3==0 else neon}" '
          f'stroke-width="{f(.6 if ring%2 else 1.0)}" opacity="{f(.065 + .023 * ring)}"/>')

    # Multi-layered membrane: asymmetrical complex curves, now unique to each update.
    for layer in range(4):
        pp = []
        for i in range(361):
            angle = math.tau*i/360
            radius = rbase + layer * 17
            radius += (34 + 2*layer)*math.sin(7*angle + shifted + layer*.18)
            radius += 14*math.sin(17*angle - shifted*.5 + layer*.32)
            radius += 7*math.sin(29*angle + shifted*2)
            pp.append((cx + radius*math.cos(angle), cy + radius*math.sin(angle)))
        a(f'<path d="{path(pp)} Z" fill="{ink if layer==0 else "none"}" '
          f'fill-opacity=".4" stroke="{cyan if layer%2 else neon}" '
          f'stroke-width="{f(1.6-layer*.25)}" opacity="{f(.19+layer*.1)}"/>')

    # Lobes, vascular trunks and recursive capillaries.
    arms = 9
    for arm in range(arms):
        theta = math.tau * arm / arms + shifted*.25
        bends = .1 * math.sin(theta*3.4 + shifted)
        trunk = []
        for t in range(56):
            dist = 20 + (t / 55.0) * (rbase+70)
            ang = theta + bends*(dist / (rbase+70)) + .065*math.sin(dist/33+arm)
            trunk.append((cx + dist*math.cos(ang), cy + dist*math.sin(ang)))
        a(f'<path d="{path(trunk)}" fill="none" stroke="{neon}" '
          f'stroke-width="2.7" opacity=".18" filter="url(#aura)"/>')
        a(f'<path d="{path(trunk)}" fill="none" stroke="{cyan if arm%2 else neon}" '
          f'stroke-width="1.5" opacity=".75"/>')
        for branch in range(3):
            start = 80 + branch*47
            side = -1 if (branch+arm)%2 else 1
            ax = theta + bends*(start/(rbase+70)) + .065*math.sin(start/33+arm)
            origin = (cx+start*math.cos(ax), cy+start*math.sin(ax))
            bp = [origin]
            for j in range(1, 19):
                t = j/18
                d = start + 65*t
                aa = ax + side*(.8*t + .2*math.sin(t*math.pi))
                bp.append((cx+d*math.cos(aa), cy+d*math.sin(aa)))
            a(f'<path d="{path(bp)}" fill="none" stroke="{cyan}" '
              f'stroke-width="{f(.85 - .13*branch)}" opacity=".38"/>')
            ex, ey = bp[-1]
            a(node(ex, ey, 1.5, neon, .7))

    # All grains have deterministic positions and lengths; public activity affects density.
    grains = 90 + min(95, sample['push_count']*3)
    for i in range(grains):
        angle = rng.uniform(0, math.tau)
        rr = rng.uniform(60, 345)
        x, y = cx + rr*math.cos(angle), cy + rr*math.sin(angle)
        if x < 670 or x > 1355 or y < 138 or y > 677:
            continue
        rad = rng.choice([.65, .85, 1.2, 1.7, 2.4])
        alpha = rng.uniform(.08, .5)
        a(node(x, y, rad, neon if i%5 else rust, alpha))
        if i%11 == 0:
            a(f'<path d="M {f(x-7)} {f(y)} h 14 M {f(x)} {f(y-7)} v 14" '
              f'stroke="#83a99a" stroke-width=".65" opacity=".36"/>')

    # Disconnected geometry, like an organism escaping a blueprint.
    for i in range(16):
        ang = (i/16)*math.tau+shifted*.14
        rr = rbase+94+rng.uniform(-13,13)
        x, y = cx+rr*math.cos(ang), cy+rr*math.sin(ang)
        r1 = rng.uniform(6,21)
        a(f'<path d="M {f(x)} {f(y)} l {f(r1*math.cos(ang+.8))} '
          f'{f(r1*math.sin(ang+.8))}" stroke="{rust if i%5==0 else cyan}" '
          f'opacity=".55" stroke-width="1.3"/>')

    a(node(cx, cy, 44, neon, .23).replace('/>', ' filter="url(#aura)"/>'))
    a('<circle cx="1010" cy="400" r="35" fill="url(#core)"/>')
    a('<circle cx="1010" cy="400" r="19" fill="#07110c"/>')
    a('<circle cx="1010" cy="400" r="7" fill="#c2ff57"/>')
    a('<circle cx="1010" cy="400" r="2" fill="#f5ffe4"/>')
    a(f'<path d="M 1010 355 V 298 M 1010 445 V 501 M 965 400 H 908 M 1055 400 H 1112" '
      f'stroke="{white}" opacity=".55" stroke-width=".9" stroke-dasharray="2 8"/>')
    a(text(1080, 158, 'MORPH / 0x'+digest[:6].upper(), 14, cyan, 400, 1))
    a(text(1310, 654, 'NOT A PORTRAIT. A TRACE.', 13, dim, 400, 1, extra='text-anchor="end"'))

    # Footer telemetry is truthful about its sampling window and outages.
    latest = 'NONE IN SAMPLE'
    if sample.get('latest_push'):
        latest = str(sample['latest_push'])[:10]
    a(text(75, 733, 'FEED', 13, dim, 400, 2))
    a(text(75, 765, state, 16, neon if state=='ONLINE' else rust, 700, 1))
    a(text(325, 733, 'PUBLIC PUSH EVENTS*', 13, dim, 400, 1))
    a(text(325, 765, str(sample['push_count']).zfill(3), 21, white, 700, 1))
    a(text(566, 733, 'ACTIVE DAYS*', 13, dim, 400, 1))
    a(text(566, 765, str(sample['activity_days']).zfill(2), 21, white, 700, 1))
    a(text(785, 733, 'LUNAR ILLUMINATION', 13, dim, 400, 1))
    a(text(785, 765, f'{illumination*100:04.1f}%', 21, white, 700, 1))
    a(text(1108, 733, 'LAST PUBLIC PUSH*', 13, dim, 400, 1))
    a(text(1108, 765, latest, 17, white, 700, 0))
    a(text(75, 807, '* SAMPLED PUBLIC EVENTS ONLY; NOT A COMPLETE CONTRIBUTION HISTORY.', 11, dim, 400, 0))
    a(text(1326, 807, iso_date(now), 11, dim, 400, 0, extra='text-anchor="end"'))
    a('</g></svg>')
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default='robdroid0110')
    parser.add_argument('--offline', action='store_true', help='Use cache, never query GitHub')
    args = parser.parse_args()
    now = datetime.now(UTC)
    cached = load_cached_sample()
    sample = None
    state = 'ONLINE'
    if not args.offline:
        try:
            sample = get_public_signal(args.user, now)
        except (urllib.error.URLError, ValueError, TimeoutError, OSError, json.JSONDecodeError) as error:
            print(f'GitHub public event sample unavailable: {type(error).__name__}')
            state = 'STALE CACHE' if cached else 'UNOBSERVED'
    else:
        state = 'OFFLINE CACHE' if cached else 'UNOBSERVED'

    if sample is None:
        sample = cached or {'push_count': 0, 'activity_days': 0, 'latest_push': None,
                            'sample_size': 0, 'sampled_at': None}

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(now, sample, state, args.user), encoding='utf-8')
    if state == 'ONLINE':
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(sample, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(f'Wrote {OUTPUT.relative_to(ROOT)} | feed={state} | '
          f'pushes={sample["push_count"]} | activity_days={sample["activity_days"]}')


if __name__ == '__main__':
    main()