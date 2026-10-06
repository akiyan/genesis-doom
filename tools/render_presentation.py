#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render the generated Canva HTML locally for visual review."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import subprocess
import os
import shutil
from local_env import load_env
load_env()
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'presentation'
REVIEW=OUT/'review'
REVIEW.mkdir(exist_ok=True)
CHROME = os.environ.get('CHROMIUM') or shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
if not CHROME:
    browsers = sorted((Path.home()/'.cache/ms-playwright').glob('chromium-*/chrome-linux*/chrome'))
    CHROME = str(browsers[-1]) if browsers else None
if not CHROME or not Path(CHROME).is_file():
    raise SystemExit('Set CHROMIUM in .env or install Chromium; see README.md')
doc=(OUT/'Presentation.html').read_text()
head=doc.split('<body>')[0]
slides=re.findall(r'<section\b.*?</section>',doc,re.S)
check='''<script>window.addEventListener('load',async()=>{await document.fonts.ready;let s=document.querySelector('.slide').getBoundingClientRect();let issues=[];for(let e of document.querySelectorAll('.txt')){let r=e.getBoundingClientRect();if(r.bottom>s.top+895||r.right>s.left+1600||r.left<s.left||r.top<s.top)issues.push({text:e.textContent,rect:[r.x,r.y,r.width,r.height]});}document.body.setAttribute('data-layout-issues',JSON.stringify(issues));});</script>'''
def render(pair):
    i,slide=pair
    path=REVIEW/f'slide-{i:02}.html'
    path.write_text(head+'<body>'+slide+check+'</body></html>')
    png=REVIEW/f'slide-{i:02}.png'
    args=[str(CHROME),'--headless','--no-sandbox','--disable-gpu','--hide-scrollbars','--no-pdf-header-footer','--window-size=1600,900','--force-device-scale-factor=1','--virtual-time-budget=1200',f'--screenshot={png}','--dump-dom',path.as_uri()]
    p=subprocess.run(args,capture_output=True,text=True,timeout=50)
    if p.returncode: raise RuntimeError(p.stderr)
    from html import unescape
    m=re.search(r'data-layout-issues="([^"]*)"',p.stdout)
    return {'slide':i,'issues':json.loads(unescape(m.group(1))) if m else ['Layout check did not execute']}
with ThreadPoolExecutor(max_workers=3) as pool:
    checks=list(pool.map(render,enumerate(slides,1)))
(REVIEW/'layout-check.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
for c in checks:
    if c['issues']: print(c)
thumbw,thumbh=480,270
sheet=Image.new('RGB',(thumbw*3,(thumbh+34)*7),'#30373b')
dr=ImageDraw.Draw(sheet)
for i in range(len(slides)):
    im=Image.open(REVIEW/f'slide-{i+1:02}.png').resize((thumbw,thumbh))
    x,y=(i%3)*thumbw,(i//3)*(thumbh+34)
    sheet.paste(im,(x,y))
    dr.text((x+10,y+thumbh+8),f'{i+1:02}',fill='white')
sheet.save(OUT/'contact-sheet.jpg')
print(f'Rendered {len(slides)} slides. Issues: {sum(bool(c["issues"]) for c in checks)}')
