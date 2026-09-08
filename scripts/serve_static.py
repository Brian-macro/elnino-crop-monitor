"""Serve the Next static export, including directory routes, on localhost."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from config import ROOT
ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=3000);args=ap.parse_args()
if not (ROOT/'out'/'index.html').exists():raise SystemExit('Run npm run build first')
print(f'El Nino Crop Monitor: http://127.0.0.1:{args.port}',flush=True)
ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(ROOT/'out'))).serve_forever()
