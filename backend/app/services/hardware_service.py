"""Hardware detection and local AI model recommendation engine.

Inspects system resources (OS, CPU cores, system RAM, GPU vendor, and VRAM)
without requiring heavy external dependencies, and recommends the optimal
quantized Qwen 2.5 Coder model size (1.5B, 3B, or 7B) for the machine.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ModelOptionInfo:
    id: str
    name: str
    size: str
    vram_approx: str
    status: str  # "recommended" | "supported" | "heavy" | "too_large"
    suitability: str


@dataclass
class HardwareProfile:
    os_name: str
    os_release: str
    architecture: str
    cpu_name: str
    cpu_cores: int
    ram_gb: float
    gpu_name: str | None
    vram_gb: float | None
    is_apple_silicon: bool
    has_cuda: bool
    hardware_tier: str  # "budget" | "mid-range" | "high-end"
    recommended_model: str
    recommended_size: str
    headline: str
    rationale: str
    models: list[ModelOptionInfo]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_ram_gb() -> float:
    """Returns total physical system RAM in gigabytes using platform built-ins."""
    sys_name = platform.system()
    try:
        if sys_name == "Windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return round(stat.ullTotalPhys / (1024**3), 1)
        elif sys_name == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            return round(int(out.strip()) / (1024**3), 1)
        else:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024**2), 1)
    except Exception as exc:
        log.warning("Could not read system RAM via OS API: %s", exc)

    return 8.0  # Safe fallback estimate


def _get_cpu_name() -> str:
    """Returns a readable CPU brand string."""
    sys_name = platform.system()
    try:
        if sys_name == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return name.strip()
        elif sys_name == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            )
            return out.strip()
        else:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "Unknown CPU"


def _get_gpu_info() -> tuple[str | None, float | None, bool]:
    """Returns (gpu_name, vram_gb, has_cuda)."""
    # 1. Try nvidia-smi directly (fastest & most accurate for NVIDIA VRAM)
    if shutil.which("nvidia-smi"):
        try:
            raw = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                timeout=2.0,
            ).strip()
            if raw:
                # First GPU in multi-GPU setup
                first_line = raw.split("\n")[0]
                parts = [p.strip() for p in first_line.split(",")]
                name = parts[0]
                vram_mb = float(parts[1]) if len(parts) > 1 else 0.0
                return name, round(vram_mb / 1024.0, 1), True
        except Exception as exc:
            log.debug("nvidia-smi check skipped or failed: %s", exc)

    # 2. Windows fallback via PowerShell CIM (for AMD, Intel Iris/Arc, or NVIDIA without nvidia-smi on PATH)
    if platform.system() == "Windows":
        try:
            cmd = "Get-CimInstance Win32_VideoController | Select-Object -Property Name, AdapterRAM | ConvertTo-Json"
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", cmd],
                text=True,
                timeout=3.0,
            ).strip()
            if out:
                data = json.loads(out)
                cards = data if isinstance(data, list) else [data]
                # Filter out basic display drivers
                candidates = [c for c in cards if c.get("Name") and "Basic" not in c.get("Name", "")]
                if candidates:
                    # Pick discrete GPU if multiple (NVIDIA/AMD over Intel integrated)
                    discrete = [c for c in candidates if any(k in c.get("Name", "").lower() for k in ("nvidia", "geforce", "rtx", "gtx", "radeon"))]
                    chosen = discrete[0] if discrete else candidates[0]
                    name = chosen.get("Name")
                    bytes_ram = chosen.get("AdapterRAM") or 0
                    vram_gb = round(bytes_ram / (1024**3), 1) if bytes_ram and bytes_ram > 0 else None
                    has_cuda = "nvidia" in (name or "").lower() or "geforce" in (name or "").lower()
                    return name, vram_gb, has_cuda
        except Exception as exc:
            log.debug("Windows CIM GPU detection skipped: %s", exc)

    # 3. macOS Apple Silicon GPU
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "Apple Silicon Integrated GPU (Metal)", None, False

    return None, None, False


def detect_hardware() -> HardwareProfile:
    """Inspects host hardware and returns a complete HardwareProfile with recommendations."""
    os_sys = platform.system()
    os_rel = platform.release()
    arch = platform.machine().lower()
    is_apple_silicon = os_sys == "Darwin" and arch == "arm64"
    cpu_cores = os.cpu_count() or 4
    cpu_name = _get_cpu_name()
    ram_gb = _get_ram_gb()
    gpu_name, vram_gb, has_cuda = _get_gpu_info()
    has_metal = is_apple_silicon

    # Nice OS string
    if os_sys == "Windows":
        os_name = f"Windows {os_rel}"
    elif os_sys == "Darwin":
        os_name = "macOS"
    else:
        os_name = f"Linux ({os_sys})"

    # --- Recommendation Logic ---
    recommended_size: str
    tier: str
    headline: str
    rationale: str

    if is_apple_silicon:
        # Apple Silicon unified memory
        if ram_gb >= 16.0:
            recommended_size = "7b"
            tier = "high-end"
            headline = "Recommended: Qwen 2.5 Coder 7B"
            rationale = (
                f"Detected Apple Silicon with {ram_gb} GB unified memory. Apple Metal offloads all 33 model layers "
                "directly to the unified memory pool, giving you high-accuracy 7B reasoning with zero VRAM bottlenecks."
            )
        else:
            recommended_size = "3b"
            tier = "mid-range"
            headline = "Recommended: Qwen 2.5 Coder 3B"
            rationale = (
                f"Detected Apple Silicon with {ram_gb} GB unified memory. The 3B model (~1.9 GB) leaves plenty of headroom "
                "for macOS system processes and your browser while executing evaluations in 1-2 seconds."
            )
    elif vram_gb is not None and vram_gb >= 11.0:
        # Desktop GPU with 12GB+ VRAM
        recommended_size = "7b"
        tier = "high-end"
        headline = "Recommended: Qwen 2.5 Coder 7B"
        rationale = (
            f"Detected dedicated GPU ({gpu_name}) with {vram_gb} GB VRAM. You have ample VRAM headroom to run the full 7B model "
            "and an 8k context window entirely on your GPU without risk of out-of-memory errors."
        )
    elif vram_gb is not None and vram_gb >= 5.5:
        # 6GB to 8GB GPUs (e.g. RTX 3050/3060/3070 Laptop, RTX 4050/4060)
        recommended_size = "3b"
        tier = "mid-range"
        headline = "Recommended: Qwen 2.5 Coder 3B"
        rationale = (
            f"Detected dedicated GPU ({gpu_name}) with {vram_gb} GB VRAM. While 7B would risk CUDA out-of-memory crashes "
            f"when sharing VRAM with your display and browser, the 3B model (~1.9 GB) fits stably with fast 1-2s grading."
        )
    elif ram_gb >= 15.0:
        # 16GB+ System RAM (either CPU-only or modest GPU)
        recommended_size = "3b"
        tier = "mid-range"
        headline = "Recommended: Qwen 2.5 Coder 3B"
        rationale = (
            f"Detected {ram_gb} GB system memory ({cpu_name}). The 3B model provides the optimal balance of reasoning quality "
            "and fast local evaluation without straining host memory."
        )
    else:
        # Constrained system (< 16 GB RAM or small mobile GPU)
        recommended_size = "1.5b"
        tier = "budget"
        headline = "Recommended: Qwen 2.5 Coder 1.5B"
        rationale = (
            f"Detected {ram_gb} GB system RAM. The 1.5B model is ultra-lightweight (~986 MB), fast, and guaranteed to run smoothly "
            "without memory pressure on your machine."
        )

    recommended_model = f"qwen2.5-coder:{recommended_size}"

    # Build comparative model cards
    models = [
        ModelOptionInfo(
            id="qwen2.5-coder:1.5b",
            name="Qwen 2.5 Coder 1.5B",
            size="1.5b",
            vram_approx="~1.2 GB VRAM",
            status="recommended" if recommended_size == "1.5b" else "supported",
            suitability="Ultra-lean and instant. Perfect for lower-power CPUs and laptops with 8 GB RAM.",
        ),
        ModelOptionInfo(
            id="qwen2.5-coder:3b",
            name="Qwen 2.5 Coder 3B",
            size="3b",
            vram_approx="~2.5 GB VRAM",
            status="recommended" if recommended_size == "3b" else "supported",
            suitability="Best all-round choice. Balances deep code comprehension with modest memory usage (1-2s evaluations).",
        ),
        ModelOptionInfo(
            id="qwen2.5-coder:7b",
            name="Qwen 2.5 Coder 7B",
            size="7b",
            vram_approx="~6.5 GB VRAM",
            status="recommended" if recommended_size == "7b" else ("heavy" if (vram_gb and vram_gb >= 6.0) or ram_gb >= 16.0 else "too_large"),
            suitability="Maximum reasoning depth. Recommended for desktop GPUs with >= 12 GB VRAM or Apple Silicon with >= 16 GB RAM.",
        ),
    ]

    return HardwareProfile(
        os_name=os_name,
        os_release=os_rel,
        architecture=arch,
        cpu_name=cpu_name,
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        is_apple_silicon=is_apple_silicon,
        has_cuda=has_cuda,
        hardware_tier=tier,
        recommended_model=recommended_model,
        recommended_size=recommended_size,
        headline=headline,
        rationale=rationale,
        models=models,
    )
