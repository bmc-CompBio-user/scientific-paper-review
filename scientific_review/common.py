from contextlib import contextmanager
from pathlib import Path
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import tempfile

PACKAGE = Path(__file__).resolve().parent


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def implementation_hash():
    return fingerprint({str(p.relative_to(PACKAGE)): digest(p) for p in sorted(PACKAGE.rglob("*"))
                        if p.is_file() and p.suffix in {".py", ".md", ".json"} and "__pycache__" not in p.parts})


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", value):
        raise ValueError("IDs must be 1-80 letters, digits, hyphens or underscores, starting with a letter/digit")
    return value


@contextmanager
def lock(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another process is using this run") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
