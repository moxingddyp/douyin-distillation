import asyncio,json,time,hashlib
from pathlib import Path
import argparse,re
parser=argparse.ArgumentParser(description='PC Bilibili single-part capture; original media stays on PC')
parser.add_argument('--bvid',required=True)
parser.add_argument('--part',type=int,default=1)
parser.add_argument('--output',required=True)
parser.add_argument('--browser-profile',required=True,help='Your existing dedicated Chrome profile; authenticate interactively first')
args=parser.parse_args()
if not re.fullmatch(r'BV[0-9A-Za-z]{10}',args.bvid) or args.part<1:
 parser.error('Expected a BV identifier and positive part number')
ROOT=Path(args.output)
PROFILE=Path(args.browser_profile).expanduser()
if not PROFILE.is_dir():
 parser.error('Browser profile must be an existing directory; authenticate it yourself first')
BV=args.bvid;CID=None;AID=None
report={'at':time.time(),'bvid':BV,'cid':CID,'aid':AID,'state':'starting','files':[]}
def save():
 p=ROOT/'capture-report.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(p)
def file_info(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
async def main():
 global CID,AID
 from playwright.async_api import async_playwright
 ROOT.mkdir(parents=True,exist_ok=False);save()
 async with async_playwright() as p:
  ctx=await p.chromium.launch_persistent_context(str(PROFILE),channel='chrome',headless=True,viewport={'width':1280,'height':900})
  try:
   async def api(path):
    r=await ctx.request.get('https://api.bilibili.com'+path,headers={'Referer':'https://www.bilibili.com/video/'+BV+'/'},timeout=30000)
    if r.status!=200:raise RuntimeError('API HTTP '+str(r.status))
    j=await r.json()
    if j.get('code')!=0:raise RuntimeError('API code '+str(j.get('code'))+': '+str(j.get('message')))
    return j['data']
   nav=await api('/x/web-interface/nav');report['login_verified']=bool(nav.get('isLogin'));save()
   if not report['login_verified']:report['state']='needs_user_confirmation_or_login';save();return
   d=await api('/x/web-interface/view?bvid='+BV)
   if d['bvid']!=BV or args.part>len(d['pages']):raise ValueError('Identity or part scope mismatch')
   selected=d['pages'][args.part-1]
   if selected['page']!=args.part:raise ValueError('Part identity mismatch')
   AID=d['aid'];CID=selected['cid'];report.update(aid=AID,cid=CID,part=args.part)
   report['identity']={k:d.get(k) for k in ['bvid','aid','cid','title','duration','pages']};report['owner']={k:d['owner'][k] for k in ['mid','name']}
   player=await api(f'/x/player/wbi/v2?aid={AID}&cid={CID}')
   report['need_login_subtitle']=player.get('need_login_subtitle');subs=player.get('subtitle',{}).get('subtitles',[])
   report['subtitles']=[]
   for i,sub in enumerate(subs):
    url=sub.get('subtitle_url');meta={k:v for k,v in sub.items() if 'url' not in k.lower()}
    if url:
     if url.startswith('//'):url='https:'+url
     r=await ctx.request.get(url,timeout=30000)
     if r.status!=200:raise RuntimeError('Subtitle HTTP '+str(r.status))
     body=await r.body();j=json.loads(body);f=ROOT/f'subtitle-{i:02d}.json';f.write_bytes(body)
     meta.update(file=file_info(f),segments=len(j.get('body',[])),classification='automatic' if sub.get('ai_type') or str(sub.get('lan','')).startswith('ai-') else 'platform_metadata_non_ai_no_independent_authorship_verification')
     report['files'].append(file_info(f))
    report['subtitles'].append(meta)
   stream=await api(f'/x/player/playurl?bvid={BV}&cid={CID}&qn=120&fnval=4048&fourk=1')
   dash=stream.get('dash',{});videos=dash.get('video',[]);audio=dash.get('audio',[])
   report['playback']={'quality':stream.get('quality'),'timelength_ms':stream.get('timelength'),'accept_quality':stream.get('accept_quality'),'video_formats':[{k:v.get(k) for k in ['id','width','height','codecs','bandwidth','frame_rate']} for v in videos],'audio_formats':[{k:v.get(k) for k in ['id','codecs','bandwidth']} for v in audio]}
   candidates=[v for v in videos if v.get('height',0)<=1080]
   if not candidates:raise RuntimeError('No applicable <=1080p stream; report rather than substitute')
   # 1080p is sufficient target for interface reading; prefer AVC at equal resolution for decoding compatibility.
   v=max(candidates,key=lambda x:(x.get('height',0),x.get('width',0),str(x.get('codecs','')).startswith('avc'),x.get('bandwidth',0)))
   a=max(audio,key=lambda x:x.get('bandwidth',0))
   report['selection']={'reason':'highest available resolution at or below1080p for software UI, AVC preferred at equal resolution','video':{k:v.get(k) for k in ['id','width','height','codecs','bandwidth','frame_rate']},'audio':{k:a.get(k) for k in ['id','codecs','bandwidth']}}
   report['state']='downloading';save()
   for name,item in [('video.m4s',v),('audio.m4s',a)]:
    f=ROOT/name
    if f.exists():raise FileExistsError(name)
    url=item.get('baseUrl') or item.get('base_url')
    r=await ctx.request.get(url,headers={'Referer':'https://www.bilibili.com/video/'+BV+'/'},timeout=180000)
    if r.status!=200:raise RuntimeError('Media HTTP '+str(r.status))
    expected=r.headers.get('content-length');body=await r.body()
    if expected and len(body)!=int(expected):raise ValueError('Media length mismatch')
    tmp=f.with_suffix('.part');tmp.write_bytes(body);tmp.replace(f);report['files'].append(file_info(f));save();await r.dispose()
   report['state']='downloaded_pending_decode';save()
  except Exception as e:
   report.update(state='failed',error_type=type(e).__name__)
   # Do not include exception URL because media URLs may be signed.
   save();raise RuntimeError('Capture failed: '+type(e).__name__) from None
  finally:await ctx.close()
if __name__=='__main__':asyncio.run(main())
