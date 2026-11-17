#!/usr/bin/env python3
"""RBD/0110 — generative, self-contained GitHub profile instrument.

No external fonts, assets, libraries, private GitHub API endpoints, or trackers.
The signals are sampled public events and deterministic orbital geometry.
Outputs are static SVG frames with optional SVG-native motion hints.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import random
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'assets'
DATA = ROOT / 'data' / 'last_signal.json'
USER = 'robdroid0110'
TWO_PI = math.tau
NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
SYNODIC = 29.530588853
BG = '#0B100F'
BG2 = '#121A18'
WHITE = '#F4F0DE'
DIM = '#82918C'
MUTED = '#50635C'
ACID = '#CEFA79'
PINK = '#ED7759'
MINT = '#81E4C3'


def q(v: float) -> str:
    return format(v, '.1f')


def xp(points: list[tuple[float,float]], closed=False):
    return 'M' + ' '.join(f'{q(x)},{q(y)}' if i == 0 else f'L{q(x)},{q(y)}' for i,(x,y) in enumerate(points)) + ('Z' if closed else '')


def tag_text(x: float, y: float, content: str, size=18, color=WHITE, weight=400, spacing=0, anchor=None, mono=False, opacity=None, rotate=None):
    attr = f' x="{q(x)}" y="{q(y)}" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}" fill="{color}"'
    attr += ' font-family="DejaVu Sans Mono, Consolas, monospace"' if mono else ' font-family="DejaVu Sans, Arial, sans-serif"'
    if anchor: attr += f' text-anchor="{anchor}"'
    if opacity is not None: attr += f' opacity="{opacity}"'
    if rotate is not None: attr += f' transform="rotate({rotate} {q(x)} {q(y)})"'
    return f'<text{attr}>{html.escape(content)}</text>'


def rect(x,y,w,h,color, opacity=1, extra=''):
    return f'<rect x="{q(x)}" y="{q(y)}" width="{q(w)}" height="{q(h)}" fill="{color}" opacity="{opacity}" {extra}/>'


def line(x1,y1,x2,y2,color=MUTED,width=1,opacity=1,extra=''):
    return f'<path d="M{q(x1)},{q(y1)}L{q(x2)},{q(y2)}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}" {extra}/>'


def circle(cx,cy,r,stroke=ACID,width=1,opacity=1,fill='none',extra=''):
    return f'<circle cx="{q(cx)}" cy="{q(cy)}" r="{q(r)}" stroke="{stroke}" stroke-width="{width}" opacity="{opacity}" fill="{fill}" {extra}/>'


def path(d, color, width=1, opacity=1, fill='none', extra=''):
    return f'<path d="{d}" stroke="{color}" stroke-width="{width}" opacity="{opacity}" fill="{fill}" {extra}/>'


def svg_begin(width,height,title,desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(desc)}</desc>',
            '''<defs>
              <radialGradient id="aura" cx="55%" cy="48%" r="65%">
                <stop stop-color="#28382A" stop-opacity=".80"/>
                <stop offset=".52" stop-color="#1A2421" stop-opacity=".32"/>
                <stop offset="1" stop-color="#0B100F" stop-opacity="0"/>
              </radialGradient>
              <linearGradient id="steel" x1="0" x2="1" y1="0" y2=".25">
                <stop stop-color="#526B5E"/><stop offset=".45" stop-color="#CEEFA4"/><stop offset="1" stop-color="#354B44"/>
              </linearGradient>
              <linearGradient id="coral" x1="0" x2="1" y1="0" y2="1">
                <stop stop-color="#F0AC71"/><stop offset="1" stop-color="#ED7759"/>
              </linearGradient>
              <pattern id="grain" width="28" height="28" patternUnits="userSpaceOnUse">
                 <circle cx="1" cy="1" r=".7" fill="#8FACA0" opacity=".24"/>
              </pattern>
              <style>
                @keyframes slowturn {from {transform:rotate(0deg)} to {transform:rotate(360deg)}}
                @keyframes counterturn {from {transform:rotate(0deg)} to {transform:rotate(-360deg)}}
                @keyframes heartbeat {0%,100%{opacity:.55}50%{opacity:1}}
                .slowturn{transform-origin:910px 412px;animation:slowturn 180s linear infinite}
                .counterturn{transform-origin:910px 412px;animation:counterturn 240s linear infinite}
                .heartbeat{animation:heartbeat 3.5s ease-in-out infinite}
                @media(prefers-reduced-motion:reduce){.slowturn,.counterturn,.heartbeat{animation:none}}
              </style>
            </defs>''',rect(0,0,width,height,BG)]


def microgrid(g,width,height,spacing=34,alpha=.12):
    g.append(rect(0,0,width,height,'url(#grain)',opacity=.36))
    for x in range(32,width,spacing):
        g.append(line(x,36,x,height-36,MUTED,.65,alpha))
    for y in range(36,height,spacing):
        g.append(line(32,y,width-32,y,MUTED,.65,alpha))


def corner(g,x,y,s=26,c=ACID):
    g.append(path(f'M{q(x+s)},{q(y)}H{q(x)}V{q(y+s)}',c,1.4,.8))


def get_events(user, now):
    headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28',
             'User-Agent':'rbd-0110-generative-instrument'}
    if os.environ.get('GH_TOKEN'): headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    events=[]
    for page in (1,2,3):
        req=urllib.request.Request(f'https://api.github.com/users/{user}/events/public?per_page=100&page={page}',headers=headers)
        with urllib.request.urlopen(req,timeout=15) as response:
            batch=json.load(response)
        if not isinstance(batch,list): raise ValueError('Public events API returned non-array')
        events += [v for v in batch if isinstance(v,dict)]
        if len(batch)<100: break
    cutoff=now-timedelta(days=90)
    pushes=[]
    for event in events:
        if event.get('type')!='PushEvent': continue
        # Ignore this profile's autogenerated churn; public project names remain private to the generator.
        if event.get('repo',{}).get('name','').lower()==f'{user}/{user}'.lower(): continue
        try: dt=datetime.fromisoformat(event['created_at'].replace('Z','+00:00'))
        except (KeyError,ValueError,AttributeError): continue
        if cutoff <= dt <= now: pushes.append(dt)
    pushes.sort()
    return {'sampled_at':now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'push_count':len(pushes),'activity_days':len({d.date() for d in pushes}),
            'sample_size':len(events),'latest_push':pushes[-1].strftime('%Y-%m-%dT%H:%M:%SZ') if pushes else None}


def signal(now,user,offline):
    if not offline:
        try:
            return get_events(user,now),'SAMPLED'
        except (urllib.error.URLError,TimeoutError,ValueError,OSError,json.JSONDecodeError):
            pass
    try:
        c=json.loads(DATA.read_text(encoding='utf-8'))
        if all(k in c for k in ('push_count','activity_days','sample_size','sampled_at')):
            return c,'CACHED'
    except (OSError,ValueError): pass
    return {'sampled_at':'NO PRIOR SAMPLE','push_count':0,'activity_days':0,'sample_size':0,'latest_push':None},'UNOBSERVED'


def render_cover(now,stats,status,seed,phase):
    r=random.Random(seed)
    w,h=1280,780
    g=svg_begin(w,h,'RBD / 0110 — THE ABSENCE OF A BIOGRAPHY',
        'Procedurally generated orbital anomaly. Geometry changes on six-hour cycles with public GitHub activity. No projects, badges or tracking pixels.')
    microgrid(g,w,h,41,.105)
    # Carbon-paper vertical strips and ruled margins.
    g.append(rect(0,0,16,h,ACID));g.append(rect(16,0,7,h,BG2))
    g.append(rect(39,30,1200,2,WHITE,.7))
    g.append(rect(39,739,1200,2,WHITE,.42))
    g.append(line(600,31,600,740,WHITE,1,.16))
    corner(g,39,48)
    g.append(tag_text(68,70,'NØ. 0110 / AUTOGENERATIVE IDENTITY',15,WHITE,700,1.4,mono=True))
    g.append(tag_text(1210,70,'RELEASE CLASS: UNKNOWN',14,DIM,400,1,anchor='end',mono=True))
    g.append(line(64,92,1211,92,MUTED,1,.6))
    # typography runs beyond tidy web component constraints; information is still readable.
    g.append(tag_text(63,199,'RBD',152,WHITE,900,-11))
    g.append(rect(69,212,382,8,ACID))
    g.append(tag_text(68,313,'/0110',115,WHITE,900,-8))
    g.append(tag_text(71,369,'D E A D  _  D R O I D',20,ACID,700,2.1,mono=True))
    g.append(line(73,404,511,404,MUTED,1,.8))
    g.append(tag_text(74,453,'IDENTITY',16,DIM,500,1.5,mono=True))
    g.append(tag_text(74,491,'NOT REQUIRED.',35,WHITE,850,-1))
    g.append(tag_text(74,541,'INTENT',16,DIM,500,1.5,mono=True))
    g.append(tag_text(74,579,'NOT DISCLOSED.',35,WHITE,850,-1))
    g.append(tag_text(75,655,'TO UNDERSTAND A SYSTEM',18,MINT,500,.1,mono=True))
    g.append(tag_text(75,679,'BECOME ITS FAILURE MODE.',18,MINT,700,.1,mono=True))
    # Dramatic negative-space surrounding organism.
    cx,cy=914,418
    g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="348" ry="329" fill="url(#aura)"/>')
    g.append('<g id="specimen">')
    # Geological annuli – cut through the portal at oblique angles.
    for k in range(16):
        rr=92+k*12.4
        pts=[]
        for i in range(113):
            t=TWO_PI*i/112
            dist=rr + (5+k*.48)*math.sin(9*t+phase*TWO_PI+k*.1)+2.5*math.sin(17*t+k*.24)
            pts.append((cx+dist*math.cos(t),cy+(dist*.935)*math.sin(t)))
        g.append(path(xp(pts),MINT if k%4==0 else WHITE,1 if k%4==0 else .7,.09 + (k%4==0)*.09))
    # Aerodynamic orbital filaments; each strand has deterministic phase, radius and optical weight.
    # This is code, not a raster asset or an image hotlink.
    for filament in range(226):
        base=filament*TWO_PI/226
        phase_shift=(seed%10000)/10000*TWO_PI
        pts=[]
        jitter=r.uniform(-.14,.14)
        for i in range(61):
            u=i/60
            theta=base + u*(3.55+0.2*math.sin(base*4))+ .12*math.sin(u*12+base*7)+jitter
            radius=(244-165*u) + 21*math.sin(7*base-12*u+phase_shift) + 7*math.sin(23*u+base*10)
            x=cx+math.cos(theta)*radius
            y=cy+math.sin(theta)*radius*.92
            pts.append((x,y))
        col=ACID if filament%17==0 else PINK if filament%29==0 else MINT if filament%4==0 else WHITE
        opacity=.5 if filament%17==0 else .2 if filament%4==0 else .075
        g.append(path(xp(pts),col,2 if filament%17==0 else .85,opacity,extra='stroke-linecap="round"'))
    # Mechanical splinters: a secondary mathematical skin, not random stars.
    for blade in range(34):
        a=blade*TWO_PI/34+phase*TWO_PI*.25
        r0=200+7*math.sin(blade*.7)
        r1=272+17*math.sin(blade*.52)
        pts=[]
        for step in range(4):
            dist=r0+(r1-r0)*step/3
            angle=a+.05*math.sin(dist*.036+blade)
            pts.append((cx+dist*math.cos(angle),cy+dist*.93*math.sin(angle)))
        g.append(path(xp(pts),WHITE if blade%5 else PINK,1.15,.4))
        if blade%3==0:
            g.append(circle(pts[-1][0],pts[-1][1],2.7,ACID,1,.72))
    # Radial circumscription with precise drafting ticks.
    g.append('<g class="slowturn">')
    for j in range(176):
        t=j*TWO_PI/176
        major=(j%11==0)
        rr=289
        length=18 if major else 7
        g.append(line(cx+rr*math.cos(t),cy+rr*math.sin(t),cx+(rr+length)*math.cos(t),cy+(rr+length)*math.sin(t),ACID if major else DIM,1.4 if major else .8,.8 if major else .32))
    g.append('</g>')
    # 3D illusion: tilted conic orbits interwoven with the actual fields.
    g.append('<g class="counterturn">')
    for k in range(7):
        theta=(k*23+7)
        g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{246-k*8}" ry="{56+k*12}" transform="rotate({theta} {cx} {cy})" fill="none" stroke="{MINT if k%2 else WHITE}" stroke-width=".85" opacity=".23"/>')
    g.append('</g>')
    # Core: a genuine aperture, not a generic glowing orb.
    g.append(circle(cx,cy,65,BG,1,1,BG))
    g.append(circle(cx,cy,65,ACID,2,.88))
    g.append(circle(cx,cy,50,MINT,1,.42,extra='stroke-dasharray="2 8"'))
    g.append(circle(cx,cy,35,WHITE,1,.22))
    g.append(tag_text(cx,cy-2,'0x',14,DIM,600,1.5,'middle',True))
    g.append(tag_text(cx,cy+29,'0110',30,WHITE,850,-1,'middle',True))
    g.append('</g>')
    # Overlaid registration notes establish scale and provenance.
    g.append(path('M657,255L722,255L762,293',WHITE,1,.45))
    g.append(tag_text(661,237,'FIG. 01 / UNBOUND SPECIMEN',12,DIM,400,.6,mono=True))
    g.append(path('M1016,608L1080,650L1184,650',WHITE,1,.45))
    g.append(tag_text(1187,646,'N=01',11,DIM,400,0,anchor='end',mono=True))
    g.append(tag_text(1210,696,'THIS IS NOT A PORTFOLIO.',13,PINK,700,1.5,'end',True))
    g.append(rect(68,714,10,10,ACID))
    g.append(tag_text(89,724,'OPERATING OUTSIDE THE DEFAULTS',12,WHITE,600,.8,mono=True))
    g.append(tag_text(1210,724,'GENERATION / '+now.strftime('%Y.%m.%d  %H:%M UTC'),12,DIM,500,.7,'end',True))
    g.append('</svg>')
    return '\n'.join(g)


def render_manifest(now,stats,status,seed,phase):
    r=random.Random(seed+7)
    w,h=1280,660
    g=svg_begin(w,h,'RBD / 0110 — THE ERROR IS AN ENTRANCE','Fictional instrument screen with three tenets and telemetry line geometry derived from public events.')
    # Variant with light paper to deliberately disrupt the dark-scroll convention.
    paper='#E9E6D6'; dark='#101C19'; ink='#20312B'; fade='#7F8B82'; orange='#CB5235'
    g.append(rect(0,0,w,h,paper))
    g.append(rect(0,0,16,h,orange))
    # grid cut into blueprint etching, not box cards
    for yy in range(35,h,31): g.append(line(36,yy,w-36,yy,ink,.7,.09))
    for xx in range(34,w,31): g.append(line(xx,38,xx,h-38,ink,.7,.06))
    g.append(rect(36,32,1206,2,dark,.7))
    g.append(tag_text(63,74,'OPERATIONAL DOGMA',19,dark,850,3))
    g.append(tag_text(1210,74,'NO RESUME FOUND / NO APOLOGY ISSUED',14,ink,500,.5,'end',True))
    g.append(line(38,98,1236,98,ink,1.2,.6))
    # Dense field fingerprint on left; offset rings create an x-ray target.
    cx,cy=352,367
    g.append(circle(cx,cy,246,ink,1,.13))
    for k in range(66):
        pp=[]
        radius=25+k*3.0
        for p in range(87):
            t=TWO_PI*p/86
            offs=(13+15*k/65)*math.sin(5*t+phase*TWO_PI+k*.12) + 5.5*math.sin(11*t+k*.35) + 3*math.sin(17*t-k*.17)
            rr=radius+offs
            pp.append((cx+rr*math.cos(t),cy+rr*math.sin(t)*.91))
        g.append(path(xp(pp),dark if k%5 else orange,.95 if k%5 else 1.6,.12 if k%5 else .3))
    # Slice diagonally across the fingerprint with annotations, not a dashboard card.
    g.append(path('M125,215L544,517',orange,2,.78))
    g.append(rect(93,508,162,30,dark))
    g.append(tag_text(103,529,'FIELD TRACE / 02',13,paper,600,.5,mono=True))
    g.append(tag_text(80,625,'01 // NON-LINEAR IDENTITY RESIDUE',12,ink,500,.5,mono=True))
    g.append(line(645,114,645,613,ink,1,.45))
    g.append(tag_text(692,164,'[ 01 ]',17,orange,750,.5,mono=True))
    g.append(tag_text(691,209,'EVERY DEFAULT',41,dark,850,-1))
    g.append(tag_text(691,256,'IS AN UNEXAMINED',35,dark,850,-1))
    g.append(tag_text(691,295,'DECISION.',41,dark,850,-1))
    g.append(line(693,315,1209,315,ink,1.2,.45))
    g.append(tag_text(692,351,'[ 02 ]',17,orange,750,.5,mono=True))
    g.append(tag_text(691,391,'ERROR MESSAGES ARE',32,dark,850,-.8))
    g.append(tag_text(691,428,'MAPS OF BORDERS.',32,dark,850,-.8))
    g.append(line(693,448,1209,448,ink,1.2,.45))
    g.append(tag_text(692,484,'[ 03 ]',17,orange,750,.5,mono=True))
    g.append(tag_text(691,524,'DISASSEMBLE',40,dark,850,-1))
    g.append(tag_text(691,571,'THE ASSUMPTION.',40,dark,850,-1))
    g.append(line(40,639,1236,639,ink,1.2,.8))
    g.append(tag_text(1220,625,'SUBJECT / RBD-0110',12,ink,500,.4,'end',True))
    g.append('</svg>')
    return '\n'.join(g)


def render_telemetry(now,stats,status,seed,phase):
    r=random.Random(seed+48)
    w,h=1280,255
    g=svg_begin(w,h,'RBD / 0110 — SAMPLE NOT LIVE','Generation timestamp, sampled public activity, lunar phase and a deterministic waveform. A design experiment, not personal statistics.')
    g.append(rect(0,0,w,h,BG))
    g.append(rect(0,0,16,h,ACID))
    g.append(line(37,19,1237,19,WHITE,1,.66))
    g.append(tag_text(55,62,'S I G N A L   /   N O T   A   S T A T U S',22,WHITE,800,1.9))
    g.append(tag_text(1210,60,'GENERATOR  /  UTC  '+now.strftime('%d %b %Y  %H:%M'),13,DIM,500,.3,'end',True))
    g.append(line(39,79,1237,79,MUTED,1,.7))
    # Actual sample metadata, not lifetime numbers or contrived performance claims.
    g.append(tag_text(61,112,'FEED  '+status,14,ACID,700,.5,mono=True))
    g.append(tag_text(405,112,'EVENTS SAMPLED  '+str(stats['sample_size']),14,WHITE,500,.4,mono=True))
    g.append(tag_text(810,112,'LUNAR PHASE  '+f'{phase:.3f}',14,WHITE,500,.4,mono=True))
    # Seismograph waveform; amplitude responds to public pushes and phase, never names.
    pts=[]
    push_factor=min(stats['push_count'],80)
    for j in range(0,1135,3):
        t=j/1135
        envelope=(.4+.6*math.sin(t*math.pi)**2)
        wave=(math.sin(2*math.pi*(4.7*t+phase))*.35+
              math.sin(2*math.pi*(19.3*t+phase*.4))*.22+
              math.sin(2*math.pi*(39*t+phase*.8))*.1+
              math.sin(2*math.pi*(87*t+phase*.12))*.06)
        wave*=1+push_factor/110
        pts.append((66+j,175+wave*49*envelope))
    g.append(path(xp(pts),ACID,1.55,.87,extra='stroke-linecap="round"'))
    g.append(line(65,174,1202,174,WHITE,.8,.17))
    for x in range(66,1204,23):
        g.append(line(x,219,x,225,MINT,.9,.3))
    g.append(tag_text(63,243,'RBD/0110 : EXTERNAL SENSOR — SAMPLED PUBLIC SIGNAL, NO REPOSITORY DISCLOSURE',11,DIM,500,.45,mono=True))
    g.append(tag_text(1212,243,'EOF / NO BIOGRAPHY',11,PINK,700,.4,'end',True))
    g.append('</svg>')
    return '\n'.join(g)


def main():
    ap=argparse.ArgumentParser(description='Rebuild the RBD/0110 post-portfolio instrument')
    ap.add_argument('--user',default=USER)
    ap.add_argument('--offline',action='store_true',help='Use the persisted sample; never make API requests')
    ap.add_argument('--at',help='UTC ISO8601 override for reproducibility, e.g. 2026-11-18T00:00:00Z')
    args=ap.parse_args()
    now=datetime.now(timezone.utc) if not args.at else datetime.fromisoformat(args.at.replace('Z','+00:00')).astimezone(timezone.utc)
    stats,status=signal(now,args.user,args.offline)
    days=(now-NEW_MOON).total_seconds()/86400
    phase=(days/SYNODIC)%1
    bucket=int(now.timestamp()//21600)
    seed=int(hashlib.sha256(f"{args.user}|{bucket}|{stats['push_count']}|{stats['activity_days']}|{phase:.4f}".encode()).hexdigest()[:16],16)
    ASSETS.mkdir(parents=True,exist_ok=True)
    files={'cover.svg':render_cover(now,stats,status,seed,phase),
           'manifest.svg':render_manifest(now,stats,status,seed,phase),
           'telemetry.svg':render_telemetry(now,stats,status,seed,phase)}
    for filename,content in files.items():
        (ASSETS/filename).write_text(content,encoding='utf-8')
        print(f'{filename}: {len(content):,} characters')
    if status=='SAMPLED':
        DATA.parent.mkdir(parents=True,exist_ok=True)
        DATA.write_text(json.dumps(stats,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('signal',status,'pushes',stats['push_count'],'sample',stats['sample_size'],'phase',f'{phase:.3f}')

if __name__=='__main__':
    main()