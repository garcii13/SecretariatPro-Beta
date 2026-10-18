import sys,json,time,os,argparse
from pathlib import Path
parser=argparse.ArgumentParser(description="Compare Mac OCR readings on synthetic and public reference fixtures; no Lab data")
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--reference',type=Path)
args=parser.parse_args()
project=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project))
os.environ['FLAGS_enable_pir_api']='0';os.environ['FLAGS_use_mkldnn']='0'
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
import ocr_engine
ocr_engine.configure(base_dir=project)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',54)
rows=[]
for kind,text in [('time',t) for t in ['00:00','01:23','09:59','12:34','18:07','20:00','99:59']]+[('score',t) for t in ['0','1','2','7','9','12','34','99','127']]:
 for variation in range(4):
  fg,bg=[('black','white'),('white','black'),('#ffd827','#101010'),('#e83838','black')][variation]
  size=(220,78) if kind=='time' else (145,78)
  image=Image.new('RGB',size,bg);ImageDraw.Draw(image).text((6,3),text,font=font,fill=fg)
  frame=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR)
  if variation==2:frame=cv2.GaussianBlur(frame,(3,3),.5)
  start=time.perf_counter()
  raw,confidence=ocr_engine._recognize(frame)
  normalized=ocr_engine.clean_time(raw) if kind=='time' else ocr_engine.clean_score(raw)
  rows.append(dict(kind=kind,expected=text,variation=variation,value=normalized,confidence=confidence,ms=(time.perf_counter()-start)*1000))
# Read-only public reference images present in the source tree.
for field,name in [('score','home'),('score','away'),('time','time')]:
 p=project/f'website/src/assets/debug-{name}.png'
 if p.is_file():
  frame=cv2.imread(str(p));start=time.perf_counter();raw,confidence=ocr_engine._recognize(frame)
  value=ocr_engine.clean_time(raw) if field=='time' else ocr_engine.clean_score(raw)
  rows.append(dict(kind=field,reference=p.name,value=value,confidence=confidence,ms=(time.perf_counter()-start)*1000))
# Ensure both signed-off specialists still load, without using OCR Lab files.
assert ocr_engine._get_spocr() is not None,ocr_engine._spocr_error
assert ocr_engine._get_spscore() is not None,ocr_engine._spscore_error
import importlib.metadata as md
result={'runtime':{p:md.version(p) for p in ['paddlepaddle','paddleocr','numpy','opencv-python','scikit-learn']},'engine':ocr_engine._engine_kind,'rows':rows}
args.output.write_text(json.dumps(result,indent=2))
print(result['runtime'],len(rows),'fixtures',flush=True)
if args.reference:
 baseline=json.loads(args.reference.read_text())
 before=baseline['rows']
 if len(before)!=len(rows) or any(a.get('expected')!=b.get('expected') or a.get('variation')!=b.get('variation') or a.get('reference')!=b.get('reference') for a,b in zip(before,rows)):
  raise SystemExit('Fixture corpus differs from the reference')
 changes=[(a,b) for a,b in zip(before,rows) if a['value']!=b['value']]
 print('Changed OCR readings:',len(changes))
 if changes:raise SystemExit('Review OCR reading differences before changing the runtime')
