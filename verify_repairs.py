"""Run offline tests in disposable storage and verify user history is unchanged."""
import argparse
import contextlib
import hashlib
import io
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
import aiohttp


def history_hashes(root):
    paths = [*root.glob("*.json"), *root.glob("*.db"), *root.joinpath("reports").glob("*")]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="test_*repair.py")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    before = history_hashes(root)
    output = io.StringIO()
    original_connect = socket.socket.connect

    def offline_connect(sock, address):
        # Windows asyncio uses a local socket pair for its wake-up pipe.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1", "localhost"):
            return original_connect(sock, address)
        raise RuntimeError("External network is disabled in offline tests")
    try:
        with tempfile.TemporaryDirectory(prefix="crypto-offline-tests-") as directory:
            original_cwd = Path.cwd()
            os.chdir(directory)
            try:
                with patch.dict(os.environ, {"DATABASE_URL": ""}), \
                     patch.object(socket.socket, "connect", new=offline_connect), \
                     patch.object(aiohttp.ClientSession, "_request", new=AsyncMock(side_effect=RuntimeError("Mock market data in offline tests"))), \
                     contextlib.redirect_stdout(output):
                    suite = unittest.defaultTestLoader.discover(str(root), pattern=args.pattern, top_level_dir=str(root))
                    result = unittest.TextTestRunner(verbosity=1).run(suite)
            finally:
                os.chdir(original_cwd)
    finally:
        after = history_hashes(root)
        changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
        if changed:
            raise RuntimeError("User history changed during tests: " + ", ".join(changed))
    print(f"Verified {len(before)} user history files unchanged.")
    if not result.wasSuccessful():
        print(output.getvalue()[-12000:])
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
