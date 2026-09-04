"""Crash-consistent, immutable raw acquisitions; indexes are reconstructible."""
from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import uuid

import numpy as np
import yaml


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_text(path, text):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    sync_dir(path.parent)


def atomic_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def csv_text(rows, fieldnames=None):
    buffer = io.StringIO()
    names = fieldnames or (list(rows[0]) if rows else [])
    writer = csv.DictWriter(buffer, fieldnames=names)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


class RunStore:
    def __init__(self, condition, plan_source, resume_run_id=""):
        self.condition = condition
        root = Path(condition.output_root) / condition.campaign_id / "runs"
        root.mkdir(parents=True, exist_ok=True)
        if resume_run_id and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,240}", resume_run_id):
            raise ValueError("resume_run_id must be an exact run basename")
        self.run_id = resume_run_id or (
            condition.condition_id + "__" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            + "__" + uuid.uuid4().hex
        )
        self.path = root / self.run_id
        if resume_run_id:
            if not self.path.is_dir() or self.path.is_symlink():
                raise ValueError("Resume run does not exist or is a symlink")
        else:
            self.path.mkdir(exist_ok=False)
            sync_dir(root)
        self._lock = (self.path / ".run.lock").open("a")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.context = {**asdict(condition), "schema_version": 1,
                            "condition_hash": condition.fingerprint(), "run_id": self.run_id,
                            "focus_policy": "local_best", "illumination_color": "green",
                            "illumination_reference_voltage_v": 20.0,
                            "illumination_voltage_source": "operator_confirmed"}
            if resume_run_id:
                old = yaml.safe_load((self.path / "resolved_condition.yaml").read_text())
                if old["condition_hash"] != condition.fingerprint():
                    raise ValueError("Resume configuration differs; create a new run")
            else:
                atomic_text(self.path / "resolved_condition.yaml", yaml.safe_dump(self.context, sort_keys=True))
                atomic_text(self.path / "plan_snapshot.yaml", plan_source)
            (self.path / "measurements").mkdir(exist_ok=True)
        except BaseException:
            self.close()
            raise

    def close(self):
        self._lock.close()

    def event(self, event_name, **data):
        event = {"timestamp_utc": utc_now(), "run_id": self.run_id,
                 "condition_id": self.condition.condition_id, "event": event_name, **data}
        with (self.path / "events.jsonl").open("a", encoding="utf-8") as handle:
            # A crash may leave a final partial line. Each new event starts on
            # its own line, so readers can discard invalid fragments.
            handle.write("\n"+json.dumps(event, allow_nan=False)+"\n")
            handle.flush()
            os.fsync(handle.fileno())

    def completed(self, verify=True):
        completed = {}
        for path in sorted((self.path / "measurements").glob("m*/attempt_*/capture_manifest.json")):
            if path.parent.name.endswith(".pending"):
                continue
            manifest = json.loads(path.read_text())
            index = manifest["measurement_index"]
            if index in completed or not 1 <= index <= self.condition.measurement_count:
                raise ValueError("Duplicate/out-of-range committed measurement")
            if verify:
                verify_capture(path, self.condition.frames_per_measurement)
            if manifest["condition_hash"] != self.condition.fingerprint():
                raise ValueError("Capture condition hash mismatch")
            completed[index] = path
        return completed

    def attempt(self, index):
        directory = self.path / "measurements" / f"m{index:03d}"
        directory.mkdir(exist_ok=True)
        numbers = [int(p.name.split('_')[1].split('.')[0]) for p in directory.glob("attempt_*")]
        number = max(numbers, default=0)+1
        path = directory / f"attempt_{number:02d}.pending"
        path.mkdir(exist_ok=False)
        sync_dir(directory)
        return number, path

    def commit(self, path, stack, frames, metadata):
        raw_path = path / "edge_raw_stack.npy"
        with raw_path.open("xb") as handle:
            np.save(handle, stack, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        atomic_text(path / "frames.csv", csv_text(frames))
        manifest = {**metadata, "schema_version": 2, "run_id": self.run_id,
                    "condition_hash": self.condition.fingerprint(),
                    "stored_frame_count": len(frames), "shape": list(stack.shape),
                    "dtype": str(stack.dtype), "raw_stack": raw_path.name,
                    "sha256": digest(raw_path), "frames_sha256": digest(path / "frames.csv"),
                    "capture_status": "complete", "analysis_status": "pending"}
        atomic_json(path / "capture_manifest.json", manifest)
        verify_capture(path / "capture_manifest.json", self.condition.frames_per_measurement)
        destination = path.with_name(path.name.removesuffix(".pending"))
        if destination.exists():
            raise FileExistsError(destination)
        os.rename(path, destination)
        sync_dir(destination.parent)
        return destination / "capture_manifest.json"

    def save_partial(self, path, frames):
        if not frames:
            return
        try:
            with (path / "partial_raw_stack.npy").open("xb") as handle:
                np.save(handle, np.stack([f["image"] for f in frames]), allow_pickle=False)
                handle.flush()
                os.fsync(handle.fileno())
            atomic_json(path / "partial_frames.json",
                        [{k:v for k,v in f.items() if k != "image"} for f in frames])
        except (OSError, ValueError):
            pass  # Never replace the original disk/capture failure with cleanup failure.

    def save_reference(self, frame, native_max):
        import cv2
        image = frame["image"]
        path = self.path / "reference_raw.npy"
        with path.open("xb") as handle:
            np.save(handle, image, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        preview = np.clip(image.astype(float)*255/native_max,0,255).astype(np.uint8)
        preview = cv2.cvtColor(preview, cv2.COLOR_GRAY2BGR)
        c = self.condition
        cv2.rectangle(preview, (c.roi_x,c.roi_y), (c.roi_x+c.roi_width,c.roi_y+c.roi_height), (0,0,255),2)
        ok, encoded = cv2.imencode(".png",preview)
        if not ok:
            raise OSError("Reference preview encoding failed")
        with (self.path/"reference_preview.png").open("xb") as handle:
            handle.write(encoded.tobytes())
            handle.flush()
            os.fsync(handle.fileno())
        sync_dir(self.path)
        return {"file":path.name, "sha256":digest(path),
                **{k:v for k,v in frame.items() if k != "image"}}

    def progress(self, status, **data):
        completed = self.completed(verify=False)
        atomic_json(self.path / "progress.json", {
            "run_id": self.run_id, "updated_utc": utc_now(), "status": status,
            "completed_measurements": sorted(completed),
            "captured_frames": len(completed)*self.condition.frames_per_measurement, **data})
        rows = [{"run_id": self.run_id, "condition_id": self.condition.condition_id,
                 "measurement_index": i, "manifest": str(p.relative_to(self.path))}
                for i, p in completed.items()]
        atomic_text(self.path / "capture_index.csv", csv_text(rows,
            ["run_id", "condition_id", "measurement_index", "manifest"]))
        return len(completed)


def verify_capture(path, expected_count=None):
    path = Path(path)
    manifest = json.loads(path.read_text())
    raw = path.parent / manifest["raw_stack"]
    if raw.parent != path.parent or raw.is_symlink():
        raise ValueError("Invalid raw stack path")
    if digest(raw) != manifest["sha256"] or digest(path.parent / "frames.csv") != manifest["frames_sha256"]:
        raise ValueError("Capture checksum mismatch")
    stack = np.load(raw, mmap_mode="r", allow_pickle=False)
    if list(stack.shape) != manifest["shape"] or str(stack.dtype) != manifest["dtype"]:
        raise ValueError("Raw shape/dtype mismatch")
    with (path.parent / "frames.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    timestamps = [int(row["source_timestamp_ns"]) for row in rows]
    count = manifest["stored_frame_count"]
    if stack.shape[0] != count or len(rows) != count or (expected_count and count != expected_count):
        raise ValueError("Incomplete capture")
    if not timestamps or timestamps[0] <= 0 or any(b <= a for a,b in zip(timestamps, timestamps[1:])):
        raise ValueError("Invalid/duplicate frame timestamps")
    return manifest
