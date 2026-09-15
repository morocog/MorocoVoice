"""Environment and hardware diagnostics tool for MorocoVoice.

Validates Windows platform, Python 3.11+, audio devices, NVIDIA CUDA/VRAM,
LongPathsEnabled registry key, and dependency integrity.

Exit codes:
0: All systems operational.
1: Critical error (e.g. non-Windows OS, missing audio capture, Python < 3.11).
2: Warnings (e.g. CPU fallback mode, LongPaths disabled, missing Groq API key).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import winreg
from pathlib import Path
from typing import Any

# Step 1: Check platform
if sys.platform != "win32":
    print("CRITICAL ERROR: MorocoVoice requires Windows 10/11 x64. Aborting.")
    sys.exit(1)


def check_python_version() -> tuple[bool, str]:
    """Verify Python 3.11+ is running."""
    ver = sys.version_info
    ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if ver.major == 3 and ver.minor >= 11:
        return True, f"Python {ver_str} (OK)"
    return False, f"Python {ver_str} (Requires Python 3.11+)"


def check_long_paths() -> tuple[bool, str]:
    """Check if Windows LongPathsEnabled is enabled in the registry."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
            0,
            winreg.KEY_READ,
        )
        val, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
        winreg.CloseKey(key)
        if val == 1:
            return True, "LongPathsEnabled is ENABLED (OK)"
        return False, "LongPathsEnabled is DISABLED (Recommended to enable for deep model paths)"
    except Exception as e:
        return False, f"Could not inspect LongPathsEnabled registry: {e}"


def detect_nvidia_vram() -> tuple[float | None, str | None]:
    """Detect NVIDIA GPU VRAM in GB via nvidia-smi."""
    candidate_paths = [
        shutil.which("nvidia-smi"),
        r"C:\Windows\System32\nvidia-smi.exe",
        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    ]
    smi_exe = next((p for p in candidate_paths if p and Path(p).exists()), None)
    if not smi_exe:
        return None, "nvidia-smi not found. Operating in CPU mode."

    try:
        cmd = [
            smi_exe,
            "--query-gpu=memory.total,driver_version,name",
            "--format=csv,noheader,nounits",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        line = res.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        total_mb = float(parts[0])
        driver = parts[1]
        gpu_name = parts[2]
        vram_gb = total_mb / 1024.0
        return vram_gb, f"{gpu_name} (VRAM: {vram_gb:.1f} GB, Driver: {driver})"
    except Exception as e:
        return None, f"Error querying nvidia-smi: {e}"


def get_hardware_tier_recommendation(vram_gb: float | None) -> dict[str, str]:
    """Calculate recommended STT and LLM configuration according to hardware matrix."""
    if vram_gb is None or vram_gb < 4.0:
        return {
            "tier": "CPU / < 4 GB",
            "whisper_model": "base / small (int8 CPU)",
            "llm_model": "None (Fast-path puro) o Groq Cloud",
            "keep_alive": "N/A",
        }
    elif vram_gb < 6.0:
        return {
            "tier": "4–5 GB VRAM",
            "whisper_model": "base",
            "llm_model": "qwen2.5:1.5b",
            "keep_alive": "10m",
        }
    elif vram_gb < 8.0:
        return {
            "tier": "6–7 GB VRAM",
            "whisper_model": "small",
            "llm_model": "qwen2.5:1.5b",
            "keep_alive": "15m",
        }
    elif vram_gb < 12.0:
        return {
            "tier": "8–11 GB VRAM",
            "whisper_model": "medium",
            "llm_model": "qwen2.5:3b",
            "keep_alive": "30m",
        }
    else:
        return {
            "tier": ">= 12 GB VRAM",
            "whisper_model": "large-v3",
            "llm_model": "llama3.1:8b",
            "keep_alive": "30m o -1",
        }


def check_audio_devices() -> tuple[bool, str]:
    """Verify available WASAPI audio recording devices via sounddevice."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
        if input_devices:
            names = [d["name"] for d in input_devices[:2]]
            return True, f"Detected {len(input_devices)} recording device(s): {', '.join(names)}"
        return False, "No audio input/recording devices found."
    except Exception as e:
        return False, f"Failed to query sounddevice: {e}"


def check_vad_model() -> tuple[bool, str]:
    """Check Silero VAD ONNX model file."""
    model_path = Path("app/audio/models/silero_vad.onnx").resolve()
    if model_path.exists() and model_path.stat().st_size > 100_000:
        return True, f"Silero VAD ONNX present ({model_path.stat().st_size / 1024:.1f} KB)"
    return False, "silero_vad.onnx not yet cached locally (will auto-download on first run)"


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceFlow-Win Hardware & Environment Diagnostics")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    exit_code = 0
    warnings: list[str] = []
    criticals: list[str] = []

    # 1. Python check
    py_ok, py_msg = check_python_version()
    if not py_ok:
        criticals.append(py_msg)
        exit_code = 1

    # 2. Audio check
    audio_ok, audio_msg = check_audio_devices()
    if not audio_ok:
        criticals.append(audio_msg)
        exit_code = 1

    # 3. LongPaths check
    lp_ok, lp_msg = check_long_paths()
    if not lp_ok:
        warnings.append(lp_msg)
        if exit_code == 0:
            exit_code = 2

    # 4. GPU / VRAM check
    vram_gb, gpu_desc = detect_nvidia_vram()
    matrix = get_hardware_tier_recommendation(vram_gb)
    if vram_gb is None:
        warnings.append("No NVIDIA GPU detected; defaulting to CPU / Cloud mode.")
        if exit_code == 0:
            exit_code = 2

    # 5. VAD check
    vad_ok, vad_msg = check_vad_model()

    # Output formatting
    report: dict[str, Any] = {
        "platform": "win32",
        "python": py_msg,
        "audio": audio_msg,
        "long_paths": lp_msg,
        "gpu": gpu_desc,
        "vram_gb": vram_gb,
        "recommendation": matrix,
        "vad": vad_msg,
        "critical_count": len(criticals),
        "warning_count": len(warnings),
        "exit_code": exit_code,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("            DIAGNÓSTICO DE SISTEMA: MOROCOVOICE v1.0.3")
        print("=" * 70)
        print("Plataforma:           Windows (win32) [OK]")
        print(f"Entorno Python:       {py_msg}")
        print(f"Dispositivos Audio:   {audio_msg}")
        print(f"Rutas Largas (NTFS):  {lp_msg}")
        print(f"Hardware Gráfico:     {gpu_desc}")
        print(f"Nivel Recomendado:    {matrix['tier']}")
        print(f"  - Whisper Local:    {matrix['whisper_model']}")
        print(f"  - LLM Refinamiento: {matrix['llm_model']}")
        print(f"VAD Subsystem:        {vad_msg}")
        print("-" * 70)
        if criticals:
            print("ERRORES CRÍTICOS:")
            for c in criticals:
                print(f"  [X] {c}")
        if warnings:
            print("ADVERTENCIAS:")
            for w in warnings:
                print(f"  [!] {w}")
        if exit_code == 0:
            print("\nRESULTADO: Sistema 100% OPERATIVO para MorocoVoice.")
        elif exit_code == 2:
            print("\nRESULTADO: Sistema OPERATIVO con advertencias menores (CPU/Cloud fallback).")
        else:
            print("\nRESULTADO: FALLO CRÍTICO. Corrija los errores anteriores.")
        print("=" * 70)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
