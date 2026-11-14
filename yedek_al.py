from pathlib import Path
import sqlite3, datetime
base=Path(__file__).resolve().parent
src=base/'demo.db'
if not src.exists():
    print('Henuz veritabani bulunamadi. Uygulamayi once acin.');raise SystemExit(1)
folder=base/'yedekler';folder.mkdir(exist_ok=True)
out=folder/('kisisel_hekimim_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.db')
with sqlite3.connect(str(src)) as inp,sqlite3.connect(str(out)) as output: inp.backup(output)
print('Yedek olusturuldu:',out)
