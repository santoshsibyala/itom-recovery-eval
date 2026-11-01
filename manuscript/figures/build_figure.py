"""Vector-only, one-column schematic; no experimental measurements encoded."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("ITOMTimes", "/System/Library/Fonts/Supplemental/Times New Roman.ttf"))
pdfmetrics.registerFont(TTFont("ITOMTimesBold", "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"))
p=Path(__file__).resolve().parent
c=canvas.Canvas(str(p/'core_failure.pdf'),pagesize=(252,188),pageCompression=1,initialFontName="ITOMTimes")
c.setTitle('Illustrative recovery failure sequence')
boxes=[(150,'Agent makes a bad change',['The configuration needs recovery.']),
       (100,'Operator makes a concurrent change',['Authorized work must be preserved.']),
       (50,'Recovery restores the agent\'s target',["But it overwrites the operator's change."]),
       (0,'Apparent success',['Health check passes; report: RECOVERED'])]
for y,title,lines in boxes:
 c.setStrokeColor(black);c.setFillColor(HexColor('#f0f0f0') if y==50 else HexColor('#ffffff'));c.setLineWidth(.75)
 c.roundRect(2,y+2,248,36,3,fill=1,stroke=1)
 c.setFillColor(black);c.setFont('ITOMTimesBold',10);c.drawCentredString(126,y+23,title)
 c.setFont('ITOMTimes',9);c.drawCentredString(126,y+10,lines[0])
 if y>0:
  c.setLineWidth(.85);c.line(126,y,126,y-9)
  path=c.beginPath();path.moveTo(123,y-6);path.lineTo(126,y-10);path.lineTo(129,y-6);c.drawPath(path,stroke=1,fill=0)
c.save()
