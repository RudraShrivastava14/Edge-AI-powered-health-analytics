"""Convert selected MIT-BIH records into compact replay files for the edge simulator.

    python ai-models/preprocessing/export_replay.py --data /path/to/mitdb --records 100 119 208
Writes edge/data/mitbih/<record>.npz (125 Hz float16 ECG, R-peak sample indices, AAMI labels).
"""

import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mitbih  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[2] / "edge" / "data" / "mitbih"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--records", nargs="+", default=["100", "119", "208"])
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for r in a.records:
        x, peaks, labels = mitbih.load_record(pathlib.Path(a.data) / r)
        x = (x - np.median(x)) / (np.std(x) + 1e-6)
        np.savez_compressed(OUT / f"{r}.npz", ecg=x.astype(np.float16), peaks=peaks.astype(np.int32), labels=labels)
        print(r, f"{(OUT / f'{r}.npz').stat().st_size/1024:.0f} KB", dict(zip(*np.unique(labels, return_counts=True))))
