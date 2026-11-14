# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/classify.py — central audio annotation service.
#
# Runs only after durable ingest has committed an audio object. Model
# backends are optional and explicit; an unavailable/uncertain result is
# needs_review, never a fabricated species.

import argparse
import csv
import glob
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import wave

from adpcm import decode_clip, write_wav


def pcm_energy(path, chunk_bytes=4096):
    total, n = 0, 0
    if path.endswith(".wav"):
        with wave.open(path, "rb") as wav:
            data = wav.readframes(wav.getnframes())
        chunks = (data[i:i + chunk_bytes]
                  for i in range(0, len(data), chunk_bytes))
    else:
        f = open(path, "rb")
        chunks = iter(lambda: f.read(chunk_bytes), b"")
    for b in chunks:
        if len(b) < 2:
            continue
        vals = struct.unpack("<%dh" % (len(b) // 2), b[:len(b) // 2 * 2])
        total += sum(abs(v) for v in vals)
        n += len(vals)
    if not path.endswith(".wav"):
        f.close()
    return total // n if n else None


def ensure_wav(path, workdir):
    """Committed .wav/.pcm/.auc → a WAV path models can consume."""
    if path.endswith(".wav"):
        return path, None
    out = os.path.join(workdir, os.path.basename(path) + ".wav")
    if path.endswith(".pcm"):
        with open(path, "rb") as f:
            pcm = f.read()
        meta = {"rate": 48000}
    elif path.endswith(".auc"):
        with open(path, "rb") as f:
            parsed = decode_clip(f.read())
        if parsed is None:
            return None, "auc-decode-failed"
        meta, pcm = parsed
    else:
        return None, "unsupported-audio"
    write_wav(out, meta, pcm)
    return out, None


def _df_scores(df, path):
    """OpenSoundscape predict() DataFrame → candidate dicts."""
    out = []
    for idx, row in df.iterrows():
        when = {"start": None, "end": None}
        if isinstance(idx, tuple) and len(idx) >= 3:
            when = {"start": float(idx[-2]), "end": float(idx[-1])}
        for label, score in row.items():
            try:
                score = float(score)
            except Exception:
                continue
            out.append({"label": str(label), "score": score, **when})
    out.sort(key=lambda c: c["score"], reverse=True)
    return out


def wav_waveform(path, target_rate=16000):
    """WAV → 16 kHz float32 mono waveform for YAMNet/ONNX."""
    import numpy as np
    with wave.open(path, "rb") as wav:
        rate, ch, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
        raw = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError("only s16le WAV is supported")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if rate == target_rate:
        return x.astype(np.float32)
    # Linear resample is acceptable here only as model-input adaptation;
    # provenance retains the source codec/rate separately.
    old = np.arange(len(x), dtype=np.float32)
    new = np.arange(0, len(x), rate / target_rate, dtype=np.float32)
    return np.interp(new, old, x).astype(np.float32)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def result_record(wav_path, node_id, mic_cal, context, backend_name,
                  backend_version, scores, ctx_scores, threshold, energy):
    """One detection line. The acoustic scores decide the label — context
    candidates ride in provenance clearly labeled, never silently
    overriding what the model heard. Low-confidence and scoreless audio
    abstain to needs_review rather than inventing a species."""
    top = scores[0] if scores else None
    # ISO 7605:2025 ambient-sound metadata — only values the record can
    # honestly state: format facts from the WAV plus whatever deployment
    # context was supplied. Self-noise is never invented.
    ambient = {"standard": "ISO 7605:2025"}
    try:
        with wave.open(wav_path, "rb") as w:
            ambient.update({"sample_rate": w.getframerate(),
                            "channels": w.getnchannels(),
                            "duration_s": round(
                                w.getnframes() / w.getframerate(), 3)})
    except Exception:
        pass
    for k in ("self_noise_db", "deployment", "gain_db"):
        if context and context.get(k) is not None:
            ambient[k] = context[k]
    rec = {
        "kind": "detection",
        "node": node_id,
        "ts": int(time.time()),
        "wav": os.path.basename(wav_path or ""),
        "energy": energy,
        "model": {"backend": backend_name, "version": backend_version},
        "label": top["label"] if top else "unknown",
        "species": top.get("species") if top else None,
        "confidence": top["score"] if top else 0.0,
        "needs_review": True,
        "status": "needs_review",
        "review_reason": None,
        "provenance": {
            "mic_cal": mic_cal,
            "ambient": ambient,
            "context": context or {},
            "context_applied": bool(ctx_scores),
            "context_adjusted_scores": ctx_scores,
        },
    }
    if not scores:
        rec["review_reason"] = "no-model-scores"
    elif top["score"] < threshold:
        rec["review_reason"] = "below-threshold"
        rec["species"] = None
    else:
        rec["needs_review"] = False
        rec["status"] = "classified"
        rec["review_reason"] = None
    return rec


class EnergyGateBackend:
    """No-model fallback: emits nothing. The honest answer a dumb
    detector gives — the pipe stays exercised end-to-end without
    inventing detections."""

    name = "none"
    version = None
    supports_context = False

    def predict(self, wav_path, context=None):
        return []


class BirdNetBackend:
    """BirdNET-Analyzer CLI → result CSV → scores. Optional lat/lon/week
    context filters the candidate list; the adjusted scores are kept
    separate in provenance, never merged into the label."""

    name = "birdnet"
    supports_context = True

    def __init__(self, min_conf=0.05):
        self.min_conf = min_conf
        try:
            from importlib.metadata import version
            self.version = version("birdnet-analyzer")
        except Exception:
            self.version = None
        self.available = subprocess.run(
            ["which", "python3"], capture_output=True).returncode == 0

    def _read(self, csv_path):
        """BirdNET result CSV → [{label, species, score}]."""
        out = []
        with open(csv_path, newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    score = float(row.get("Confidence") or 0)
                except ValueError:
                    continue
                if score < self.min_conf:
                    continue
                out.append({"label": row.get("Common name") or "unknown",
                            "species": row.get("Scientific name"),
                            "score": score})
        return sorted(out, key=lambda r: -r["score"])

    def predict(self, wav_path, context=None):
        try:
            with tempfile.TemporaryDirectory() as td:
                cmd = ["python3", "-m", "birdnet_analyzer.analyze",
                       "--i", wav_path, "--o", td, "--rtype", "csv",
                       "--min_conf", str(self.min_conf)]
                if context:
                    for k, flag in (("lat", "--lat"), ("lon", "--lon"),
                                    ("week", "--week")):
                        if context.get(k) is not None:
                            cmd += [flag, str(context[k])]
                subprocess.run(cmd, check=True, capture_output=True)
                csvs = sorted(glob.glob(os.path.join(td, "*.csv")))
                return self._read(csvs[0]) if csvs else []
        except Exception:
            return []


class OpenSoundscapeBackend:
    """OpenSoundscape seam (the adopted OSS): pretrained model when the
    package is installed; empty when it is not — same honest abstain."""

    name = "opensoundscape"
    supports_context = False

    def __init__(self, model_path=None, min_conf=0.05):
        self.model_path = model_path
        self.min_conf = min_conf
        self._ml = None
        try:
            from opensoundscape.analyze import cosine_similarity
            from opensoundscape.ml import TrainGUI
            self._ml = TrainGUI()
            if model_path:
                self._ml.load_model(model_path)
            self.version = getattr(self._ml, "version", "opensoundscape")
        except Exception:
            self.version = None

    def predict(self, wav_path, context=None):
        if self._ml is None:
            return []
        try:
            df = self._ml.predict(wav_path, min_conf=self.min_conf)
            return [{"label": s["label"], "species": s["label"],
                     "score": s["score"]}
                    for s in _df_scores(df, wav_path)
                    if s["score"] >= self.min_conf]
        except Exception:
            return []


class YamNetBackend:
    """YAMNet seam: labels file + optional sha256 pin; scores are the
    classifier's top entries above min_conf. Absent model → abstain."""

    name = "yamnet"
    supports_context = False

    def __init__(self, model_path=None, labels_path=None,
                 sha256=None, min_conf=0.05):
        self.model_path = model_path
        self.min_conf = min_conf
        self.version = None
        self.labels = []
        if labels_path and os.path.exists(labels_path):
            with open(labels_path) as fh:
                self.labels = [ln.strip() for ln in fh if ln.strip()]
        if sha256 and model_path and os.path.exists(model_path):
            try:
                if sha256_file(model_path) != sha256:
                    self.model_path = None     # pin mismatch: refuse
            except Exception:
                self.model_path = None

    def predict(self, wav_path, context=None):
        return []          # scoring requires the tflite runtime; seam only


def logmel(waveform, rate, n_mels, fmin, fmax, n_fft=2048, hop=320,
           win=1024):
    """float32 mono waveform → log-mel [n_mels, T] for embedding models.
    Frontend params come from the heads file — config, not code — so a
    Perch/PANNs-class ONNX model plugs in without new first-party DSP."""
    import numpy as np
    x = np.asarray(waveform, dtype=np.float32)
    if len(x) < win:
        x = np.pad(x, (0, win - len(x)))
    n_frames = 1 + (len(x) - win) // hop
    frames = np.lib.stride_tricks.as_strided(
        x, shape=(n_frames, win),
        strides=(x.strides[0] * hop, x.strides[0])).copy()
    frames *= np.hanning(win).astype(np.float32)
    spec = np.abs(np.fft.rfft(frames, n=n_fft, axis=1)) ** 2
    freqs = np.fft.rfftfreq(n_fft, 1.0 / rate)
    # triangular mel filterbank
    def hz2mel(f): return 2595.0 * np.log10(1.0 + f / 700.0)
    def mel2hz(m): return 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    mels = np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2)
    pts = mel2hz(mels)
    fb = np.zeros((n_mels, len(freqs)), dtype=np.float32)
    for i in range(n_mels):
        lo, ce, hi = pts[i], pts[i + 1], pts[i + 2]
        up = (freqs - lo) / max(ce - lo, 1e-9)
        dn = (hi - freqs) / max(hi - ce, 1e-9)
        fb[i] = np.maximum(0.0, np.minimum(up, dn))
    mel = spec @ fb.T
    return np.log(mel + 1e-6).T.astype(np.float32)   # [n_mels, T]


class OnnxEmbedBackend:
    """Pretrained-embedding seam (Perch/PANNs-class ONNX): embeds the clip
    with ONNX Runtime, scores cosine similarity against few-shot centroid
    heads. Model + heads JSON are deployment artifacts — absent either,
    the backend abstains exactly like the other seams. The heads file:
    {"sample_rate":16000,"n_mels":64,"fmin":50,"fmax":14000,
     "heads":{"label":[centroid...]}}."""

    name = "onnx-embed"
    supports_context = False

    def __init__(self, model_path=None, heads_path=None, min_conf=0.05):
        self.min_conf = min_conf
        self.version = None
        self._sess = None
        self._heads = []
        self._fe = {}
        if not (model_path and heads_path):
            return
        try:
            import onnxruntime as ort
            self._sess = ort.InferenceSession(model_path)
            with open(heads_path) as fh:
                spec = json.load(fh)
            self._fe = {k: spec[k] for k in
                        ("sample_rate", "n_mels", "fmin", "fmax")
                        if k in spec}
            self._fe.setdefault("sample_rate", 16000)
            self._fe.setdefault("n_mels", 64)
            self._fe.setdefault("fmin", 50.0)
            self._fe.setdefault("fmax", 14000.0)
            import numpy as np
            for label, vec in (spec.get("heads") or {}).items():
                v = np.asarray(vec, dtype=np.float32)
                n = np.linalg.norm(v)
                if n > 0:
                    self._heads.append((label, v / n))
            self.version = "onnx-embed:" + os.path.basename(model_path)
        except Exception:
            self._sess = None
            self._heads = []
            self.version = None

    def predict(self, wav_path, context=None):
        if self._sess is None or not self._heads:
            return []
        try:
            import numpy as np
            x = wav_waveform(wav_path,
                             target_rate=self._fe["sample_rate"])
            mel = logmel(x, self._fe["sample_rate"], self._fe["n_mels"],
                         self._fe["fmin"], self._fe["fmax"])
            inp = self._sess.get_inputs()[0]
            feed = {inp.name: mel[None, :, :].astype(np.float32)}
            emb = np.asarray(self._sess.run(None, feed)[0]).reshape(-1)
            n = np.linalg.norm(emb)
            if n == 0:
                return []
            emb = emb / n
            out = [{"label": label, "species": label,
                    "score": float(np.dot(emb, c))}
                   for label, c in self._heads]
            return sorted((c for c in out if c["score"] >= self.min_conf),
                          key=lambda c: -c["score"])
        except Exception:
            return []


def load_backend(kind, model_path=None, min_conf=0.05,
                 yamnet_labels=None, yamnet_sha256=None,
                 heads_path=None):
    if kind == "birdnet":
        return BirdNetBackend(min_conf=min_conf)
    if kind == "opensoundscape":
        return OpenSoundscapeBackend(model_path, min_conf)
    if kind == "yamnet":
        return YamNetBackend(model_path, yamnet_labels, yamnet_sha256,
                             min_conf)
    if kind == "onnx-embed":
        return OnnxEmbedBackend(model_path, heads_path, min_conf)
    return EnergyGateBackend()


def classify_file(path, backend, node_id, mic_cal, context, threshold):
    """One spool file → one detection record. Acoustic scores decide the
    label; context scores annotate provenance when the backend supports
    it. Conversion/model failures abstain to needs_review."""
    energy = 0
    try:
        energy = pcm_energy(path)
    except Exception:
        pass
    scores, ctx_scores, model_err, wav = [], [], None, path
    try:
        wav, werr = ensure_wav(path, tempfile.mkdtemp(prefix="ecocell-cls-"))
        if werr or wav is None:
            model_err = werr or "wav-convert-failed"
        else:
            scores = backend.predict(wav)
            if context and getattr(backend, "supports_context", False):
                ctx_scores = backend.predict(wav, context)
    except Exception:
        model_err = "model-error"
    rec = result_record(wav, node_id, mic_cal, context,
                        getattr(backend, "name", "none"),
                        getattr(backend, "version", None),
                        scores, ctx_scores, threshold, energy)
    if model_err:
        rec.update({"status": "needs_review", "needs_review": True,
                    "review_reason": model_err})
    return rec
def load_state(path):
    try:
        return set(json.load(open(path)))
    except Exception:
        return set()


def save_state(path, seen):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(sorted(seen), fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def run(spool, out, review_out, node_id, mic_cal, once, poll_s, backend,
        context, threshold, state_path):
    seen = load_state(state_path)
    sys.stderr.write("classifier up: spool=%s model=%s\n"
                     % (spool, getattr(backend, "name", "none")))
    with open(out, "a") as fh, open(review_out, "a") as review:
        while True:
            for name in sorted(os.listdir(spool)):
                # durable_ingest writes .auc + decoded .wav; the WAV is the
                # canonical model input, so .auc never double-counts.
                if name in seen or not name.endswith((".pcm", ".wav")):
                    continue
                seen.add(name)
                try:
                    rec = classify_file(os.path.join(spool, name), backend,
                                        node_id, mic_cal, context, threshold)
                except Exception as e:
                    rec = {"kind": "audio-annotation", "node": node_id,
                           "audio_said": os.path.splitext(name)[0],
                           "label": "unknown", "status": "needs_review",
                           "needs_review": True,
                           "review_reason": "classifier-error:%s" % type(e).__name__,
                           "model": {"backend": getattr(backend, "name", "none")},
                           "provenance": {"source": name}}
                if rec is not None:
                    line = json.dumps(rec, separators=(",", ":")) + "\n"
                    (review if rec.get("needs_review") else fh).write(line)
                    (review if rec.get("needs_review") else fh).flush()
            save_state(state_path, seen)
            if once:
                return
            time.sleep(poll_s)


def main():
    p = argparse.ArgumentParser(description="EcoCell central classifier")
    p.add_argument("--spool", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--review-out", default="review.jsonl")
    p.add_argument("--state", default=".classifier_state.json")
    p.add_argument("--backend", choices=("none", "birdnet", "opensoundscape",
                                         "yamnet", "onnx-embed"),
                   default="none")
    p.add_argument("--opso-model")
    p.add_argument("--onnx-model")
    p.add_argument("--onnx-heads",
                   help="few-shot centroid heads JSON for onnx-embed")
    p.add_argument("--yamnet-model")
    p.add_argument("--yamnet-labels")
    p.add_argument("--yamnet-sha256")
    p.add_argument("--node", default="node-7")
    p.add_argument("--mic-cal")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--week", type=int)
    p.add_argument("--habitat")
    p.add_argument("--site")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-conf", type=float, default=0.05)
    p.add_argument("--once", action="store_true")
    p.add_argument("--poll", type=float, default=2.0)
    a = p.parse_args()
    context = {k: v for k, v in {"lat": a.lat, "lon": a.lon,
                                 "week": a.week, "habitat": a.habitat,
                                 "site": a.site}.items() if v is not None}
    model_path = (a.yamnet_model if a.backend == "yamnet"
                  else a.opso_model if a.backend == "opensoundscape"
                  else a.onnx_model if a.backend == "onnx-embed"
                  else None)
    backend = load_backend(a.backend, model_path, a.min_conf,
                           a.yamnet_labels, a.yamnet_sha256,
                           heads_path=a.onnx_heads)
    run(a.spool, a.out, a.review_out, a.node, a.mic_cal, a.once, a.poll,
        backend, context, a.threshold, a.state)


if __name__ == "__main__":
    main()