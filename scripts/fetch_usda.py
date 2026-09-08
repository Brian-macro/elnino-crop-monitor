"""Official PSD archive. Same URL corrections create new content hashes, never overwrite history."""
from db import connect
from archive import download,failed
from normalize import ingest_psd
from config import PSD_URL

def main():
    con=connect()
    try:
        doc=download(con,'usda_psd',PSD_URL,suffix='.zip',title='USDA PSD latest snapshot')
        ingest_psd(con,doc)
    except Exception as e:
        failed(con,'usda_psd',e);return 2
    finally:con.close()
    return 0
if __name__=='__main__':raise SystemExit(main())
