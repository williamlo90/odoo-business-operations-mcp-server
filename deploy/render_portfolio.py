"""Render GitHub figures from recorded synthetic receipts. Requires Pillow; no model/API calls."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/assets'
DATA=json.loads((ROOT/'docs/demo/recording.json').read_text())
OUT.mkdir(exist_ok=True)
def font(n,bold=False,mono=False):
    windows=Path('C:/Windows/Fonts')/('consola.ttf' if mono else 'segoeuib.ttf' if bold else 'segoeui.ttf')
    linux=Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSansMono.ttf' if mono else 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    return ImageFont.truetype(str(windows if windows.exists() else linux),n)
def canvas(w,h,color):
    im=Image.new('RGB',(w,h),color);return im,ImageDraw.Draw(im)
def text(d,xy,s,n=26,color='#19242c',bold=False,mono=False):
    f=font(n,bold,mono);b=d.textbbox(xy,s,font=f)
    assert b[2]<d._image.width-15 and b[3]<d._image.height-12,(s,b)
    d.text(xy,s,font=f,fill=color)
im,d=canvas(1440,730,'#f3f0e9')
text(d,(64,44),'ODOO / BUSINESS OPERATIONS MCP',22,'#72516f',True)
text(d,(64,105),'AI assistance.',76,bold=True)
text(d,(64,196),'Verified business outcomes.',76,bold=True)
text(d,(68,312),'Exact source records. Separate approval. Recoverable execution.',29,'#535f65')
for i,(label,title,lines) in enumerate([
 ('01 / PREPARE','Source-bound preview',['Exact customer and products','Versioned proposal + total']),
 ('02 / APPROVE','Explicit authority',['Separate approver identity','Approval tied to payload hash']),
 ('03 / VERIFY','One checked result',['Actual Odoo read-back','Stable operation and replay'])]):
 x=64+i*445;d.rounded_rectangle((x,402,x+419,626),radius=14,fill='#ffffff')
 text(d,(x+24,423),label,20,'#72516f',True);text(d,(x+24,469),title,27,bold=True)
 for j,line in enumerate(lines):text(d,(x+24,526+j*35),line,21,'#536269')
text(d,(68,665),'LOCAL ODOO VALIDATION   /   124 workload tasks   /   31 verified writes',23,'#536269')
im.save(OUT/'overview.png')
e=DATA['events'];p=e[2]['output'];o=e[5]['output'];r=o['result']['record']
assert o['id']==e[7]['output']['id'] and DATA['ledger_count']==DATA['order_count']==1
cards=[('proposal','01 / PREPARE','Review before creation',[
 'customer   OPS-A-001','company    '+str(p['preview']['company_id']),
 'items      2 x P1 + 1 x P2','total      IDR '+format(float(p['preview']['total']),',.0f'),
 'proposal   '+p['id'][:18]+'...']),
 ('approval','02 / APPROVE','The role boundary holds',[
 'actor      '+e[3]['role'],e[3]['output'],'',
 'approver   '+e[4]['role'],'approval   '+e[4]['output']['id'][:18]+'...']),
 ('receipt','03 / VERIFY','Inspect the actual draft',[
 'status     '+o['status'],'record     '+r['name'],'state      '+r['state'],
 'total      IDR '+format(float(r['total']),',.0f'),'operation  '+o['id'][:18]+'...']),
 ('replay','04 / RECOVER','Resume the same operation',[
 'fresh CLI  status lookup','replay     original execution key','status     '+e[7]['output']['status'],
 'ledger     '+str(DATA['ledger_count'])+' entry','orders     '+str(DATA['order_count'])+' draft'])]
for name,label,title,lines in cards:
 im,d=canvas(940,560,'#17232c');text(d,(40,32),label,22,'#b7a0ba',True)
 text(d,(40,89),title,38,'#ffffff',True);d.line((40,162,900,162),fill='#43525e',width=2)
 for j,line in enumerate(lines):text(d,(40,199+j*47),line,27,'#dde8e8',mono=True)
 text(d,(40,504),'Recorded CLI receipt summary / synthetic sandbox',20,'#9faeb7')
 im.save(OUT/(name+'.png'))
im,d=canvas(1440,740,'#f3f0e9')
text(d,(54,38),'HOW AUTHORITY MOVES THROUGH THE SYSTEM',23,'#72516f',True)
boxes=[(54,135,420,310,'Caller + assistant',['Typed intent or clarification','Reference CLI / shared skills']),
 (534,135,900,310,'Custom MCP',['10 allowlisted tools','Authenticated stdio']),
 (1014,135,1380,310,'Domain service',['Scope, proposal, approval','FastAPI + PostgreSQL']),
 (54,440,420,615,'Worker + journal',['Scoped jobs and leases','No automatic approval']),
 (534,440,900,615,'Separate approver',['Review the exact preview','Authorize its payload hash']),
 (1014,440,1380,615,'Odoo + ledger',['Signed business action','Actual result + read-back'])]
for x,y,x2,y2,title,lines in boxes:
 d.rounded_rectangle((x,y,x2,y2),radius=12,fill='white')
 text(d,(x+22,y+23),title,29,bold=True)
 for j,line in enumerate(lines):text(d,(x+22,y+79+j*33),line,21,'#536269')
for x1,y1,x2,y2 in [(420,220,534,220),(900,220,1014,220),(1200,310,1200,440),(420,520,495,520),(495,520,495,300),(495,300,534,280),(900,500,968,500),(968,500,968,277),(968,277,1014,277)]:
 d.line((x1,y1,x2,y2),fill='#72516f',width=3)
for x,y in [(534,220),(1014,220),(534,280),(1014,277)]:d.polygon([(x,y),(x-10,y-7),(x-10,y+7)],fill='#72516f')
d.polygon([(1200,440),(1193,430),(1207,430)],fill='#72516f')
text(d,(54,665),'Business success is reported only after the Odoo result has been checked.',25,'#536269')
im.save(OUT/'architecture.png')
print('Rendered six documentation figures from the recorded demo.')
