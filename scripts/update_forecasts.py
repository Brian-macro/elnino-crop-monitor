"""Daily forecast checks against the persisted baseline; no historical downloads."""
import sys
from update_all import main


if __name__ == '__main__':
    # Put the fixed group last so this entry point cannot become a full refresh.
    raise SystemExit(main([*sys.argv[1:], '--group', 'forecasts']))
