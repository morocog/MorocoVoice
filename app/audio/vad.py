"""Voice Activity Detection (VAD) subsystem for MorocoVoice.

STRICT CONTRACT: ZERO PYTORCH.
Uses onnxruntime to execute silero_vad.onnx with automatic failover to
energy-based RMS software VAD if the ONNX model cannot be retrieved or loaded.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort

from app.contracts import VADMode
from app.logging_setup import get_logger

logger = get_logger("vad")

CANDIDATE_URLS: list[str] = [
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx",
    "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx",
    "https://github.com/snakers4/silero-vad/raw/v5.1.2/src/silero_vad/data/silero_vad.onnx",
]

DEFAULT_MODEL_DIR = Path(__file__).parent / "models"
MODEL_FILE_NAME = "silero_vad.onnx"


class VoiceActivityDetector:
    """Hybrid Voice Activity Detector (Silero ONNX with RMS Fallback)."""

    def __init__(
        self,
        model_dir: Path | None = None,
        speech_threshold: float = 0.5,
        rms_threshold: float = 0.015,
        sample_rate: int = 16000,
    ) -> None:
        self.speech_threshold = speech_threshold
        self.rms_threshold = rms_threshold
        self.sample_rate = sample_rate
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.model_path = self.model_dir / MODEL_FILE_NAME

        self.mode = VADMode.RMS
        self._session: ort.InferenceSession | None = None
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, 64), dtype=np.float32)

        self._initialize()

    def _initialize(self) -> None:
        """Attempt to acquire and validate Silero VAD session; fall back to RMS on failure."""
        self.model_dir.mkdir(parents=True, exist_ok=True)

        if not self.model_path.exists() or self.model_path.stat().st_size == 0:
            logger.info("silero_vad.onnx not found locally. Attempting automatic acquisition...")
            self._acquire_model()

        if self.model_path.exists() and self.model_path.stat().st_size > 0:
            try:
                # Set CPU provider exclusively for maximum compatibility
                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                opts.log_severity_level = 3  # Error only
                self._session = ort.InferenceSession(
                    str(self.model_path), sess_options=opts, providers=["CPUExecutionProvider"]
                )
                self.mode = VADMode.SILERO
                logger.info("Silero VAD initialized successfully in ONNX CPU mode.")
                return
            except Exception as e:
                logger.warning("Failed to initialize ONNX session for %s: %s", self.model_path, e)

        # Fallback to software RMS
        self.mode = VADMode.RMS
        logger.warning("Operating in fallback software VAD mode: VAD: RMS (degradado).")

    def _acquire_model(self) -> None:
        """Iterate over candidate URLs to download silero_vad.onnx."""
        for url in CANDIDATE_URLS:
            try:
                logger.info("Attempting Silero VAD download from %s", url)
                temp_dest = self.model_path.with_suffix(".tmp")
                req = urllib.request.Request(
                    url, headers={"User-Agent": "MorocoVoice-Bootstrap/1.0.1"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp, open(temp_dest, "wb") as f:
                    f.write(resp.read())

                if temp_dest.stat().st_size > 100_000:  # silero_vad.onnx is ~1.8 MB
                    temp_dest.replace(self.model_path)
                    logger.info("Silero VAD model downloaded successfully from %s", url)
                    return
                else:
                    if temp_dest.exists():
                        temp_dest.unlink()
            except Exception as exc:
                logger.warning("Candidate download failed from %s: %s", url, exc)

        logger.error("Could not download silero_vad.onnx from any candidate repository.")

    def reset(self) -> None:
        """Reset internal recurrent state and context tensors."""
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, 64), dtype=np.float32)

    def is_speech_chunk(self, audio_chunk: np.ndarray) -> bool:
        """Determine if a 16kHz audio chunk contains human voice activity."""
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.squeeze()

        if len(audio_chunk) == 0:
            return False

        # If running in Silero ONNX mode
        if self.mode == VADMode.SILERO and self._session is not None:
            try:
                # Silero expects 512 samples at 16kHz
                chunk = audio_chunk.astype(np.float32)
                if len(chunk) != 512:
                    if len(chunk) > 512:
                        chunk = chunk[:512]
                    else:
                        chunk = np.pad(chunk, (0, 512 - len(chunk)))

                chunk_input = np.expand_dims(chunk, axis=0)  # Shape: (1, 512)
                sr_input = np.array(self.sample_rate, dtype=np.int64)

                # Prepend 64 context samples for Silero VAD v5
                x = np.concatenate([self._context, chunk_input], axis=1)  # Shape: (1, 576)
                self._context = chunk_input[:, -64:]

                # Check model input names
                input_names = [inp.name for inp in self._session.get_inputs()]
                inputs: dict[str, np.ndarray] = {input_names[0]: x}

                if "sr" in input_names:
                    inputs["sr"] = sr_input
                if "state" in input_names:
                    inputs["state"] = self._state

                outputs = self._session.run(None, inputs)
                output_prob = float(outputs[0][0][0]) if outputs[0].ndim > 1 else float(outputs[0][0])

                # Update recurrent state if outputted
                if len(outputs) > 1 and outputs[1].shape == self._state.shape:
                    self._state = outputs[1]

                return output_prob >= self.speech_threshold
            except Exception as e:
                logger.warning("Silero inference error: %s. Falling back to RMS chunk analysis.", e)

        # Fallback RMS computation
        return self._is_speech_rms(audio_chunk)

    def _is_speech_rms(self, audio_chunk: np.ndarray) -> bool:
        """Compute root-mean-square energy and compare to configured threshold."""
        if len(audio_chunk) == 0:
            return False
        rms = float(np.sqrt(np.mean(np.square(audio_chunk, dtype=np.float32))))
        return rms >= self.rms_threshold

    def get_mode(self) -> VADMode:
        """Return the active VAD operational mode."""
        return self.mode
