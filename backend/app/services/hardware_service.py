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
from dataclasses import asdict, dataclass
from functools import lru_cache
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


@lru_cache
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
        if ram_gb >= 24.0:
            recommended_size = "9b"
            recommended_model = "qwen3.5:9b"
            tier = "high-end"
            headline = "Recommended: Qwen 3.5 9B (The Heavy Generalist)"
            rationale = (
                f"Detected Apple Silicon with {ram_gb} GB unified memory. Apple Metal offloads model layers "
                "directly to unified memory, giving you high-capacity 9B multimodal reasoning with zero VRAM bottlenecks."
            )
        elif ram_gb >= 16.0:
            recommended_size = "7b"
            recommended_model = "qwen2.5-coder:7b"
            tier = "mid-range"
            headline = "Recommended: Qwen2.5-Coder 7B (The Technical Specialist)"
            rationale = (
                f"Detected Apple Silicon with {ram_gb} GB unified memory. The 7B technical specialist model provides "
                "exceptional code and logic precision with ample headroom for macOS system processes."
            )
        else:
            recommended_size = "4b"
            recommended_model = "qwen3.5:4b"
            tier = "budget"
            headline = "Recommended: Qwen 3.5 4B / Gemma 4 E4B (The Speed Demon)"
            rationale = (
                f"Detected Apple Silicon with {ram_gb} GB unified memory. The 4B speed-demon model leaves plenty of headroom "
                "while executing evaluations with near-instant token streaming."
            )
    elif vram_gb is not None and vram_gb >= 11.0:
        # Desktop GPU with 12GB+ VRAM
        recommended_size = "9b"
        recommended_model = "qwen3.5:9b"
        tier = "high-end"
        headline = "Recommended: Qwen 3.5 9B (The Heavy Generalist)"
        rationale = (
            f"Detected dedicated GPU ({gpu_name}) with {vram_gb} GB VRAM. You have ample VRAM headroom to run the full 9B "
            "multimodal generalist model entirely on your GPU without risk of out-of-memory errors."
        )
    elif vram_gb is not None and vram_gb >= 5.5:
        # 6GB to 10GB GPUs (e.g. RTX 3060/3070/4060)
        recommended_size = "7b"
        recommended_model = "qwen2.5-coder:7b"
        tier = "mid-range"
        headline = "Recommended: Qwen2.5-Coder 7B (The Technical Specialist)"
        rationale = (
            f"Detected dedicated GPU ({gpu_name}) with {vram_gb} GB VRAM. The 7B Technical Specialist model (~4.7 GB) "
            "fits comfortably on your GPU, providing high-precision code and logic grading."
        )
    elif ram_gb >= 15.0:
        # 16GB+ System RAM (either CPU-only or modest GPU)
        recommended_size = "7b"
        recommended_model = "qwen2.5-coder:7b"
        tier = "mid-range"
        headline = "Recommended: Qwen2.5-Coder 7B (The Technical Specialist)"
        rationale = (
            f"Detected {ram_gb} GB system memory ({cpu_name}). The 7B model provides high-precision technical comprehension "
            "and reliable local evaluations."
        )
    else:
        # Constrained system (< 16 GB RAM or small mobile GPU)
        recommended_size = "4b"
        recommended_model = "qwen3.5:4b"
        tier = "budget"
        headline = "Recommended: Qwen 3.5 4B / Gemma 4 E4B (The Speed Demon)"
        rationale = (
            f"Detected {ram_gb} GB system RAM. The 4B speed-demon model is lightweight, fast, and guaranteed to run smoothly "
            "without memory pressure on your machine."
        )

    # Build comparative model cards for the 3 allowed models
    models = [
        ModelOptionInfo(
            id="qwen3.5:9b",
            name="Qwen 3.5 9B (The Heavy Generalist)",
            size="9b",
            vram_approx="~5.3 GB VRAM",
            status="recommended" if recommended_size == "9b" else (
                "supported" if (vram_gb and vram_gb >= 7.5) or (is_apple_silicon and ram_gb >= 16.0) or ram_gb >= 24.0
                else ("heavy" if (vram_gb and vram_gb >= 5.5) or ram_gb >= 16.0 else "too_large")
            ),
            suitability="Dense hybrid reasoning & multimodal evaluation. High-capacity general intelligence workhorse.",
        ),
        ModelOptionInfo(
            id="qwen2.5-coder:7b",
            name="Qwen2.5-Coder 7B (The Technical Specialist)",
            size="7b",
            vram_approx="~4.7 GB VRAM",
            status="recommended" if recommended_size == "7b" else (
                "supported" if (vram_gb and vram_gb >= 5.5) or ram_gb >= 16.0 else "heavy"
            ),
            suitability="High-precision code & logic grading. Deep syntax comprehension and technical specialization.",
        ),
        ModelOptionInfo(
            id="qwen3.5:4b",
            name="Qwen 3.5 4B / Gemma 4 E4B (The Speed Demon)",
            size="4b",
            vram_approx="~2.5 GB VRAM",
            status="recommended" if recommended_size == "4b" else "supported",
            suitability="Blistering fast token generation & lightweight memory footprint. Ultra-low latency responses.",
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


def get_vram_metrics(
    model_name: str | None = None,
    ollama_base_url: str = "http://localhost:11434",
) -> dict[str, Any]:
    """Retrieves live VRAM and GPU memory telemetry:
    - capacity_gb: Total VRAM capacity on the machine (e.g. 8.0 GB)
    - available_gb: Free unallocated VRAM headroom (e.g. 3.3 GB)
    - used_gb: Currently used VRAM across the system (e.g. 4.7 GB)
    - model_vram_gb: Exact VRAM occupied by the selected/active model in Ollama
    - model_approx_gb: Approximate VRAM footprint when loaded
    - model_loaded: Whether the model is currently resident in VRAM
    - gpu_name: Name of detected GPU device
    - memory_source: where the capacity figure came from ("nvidia-smi",
      "apple-unified", "gpu-adapter", "system-ram", "cloud")
    - usage_measured: False when used/available are not real readings. Only
      nvidia-smi and macOS page counts are measured; elsewhere the split is a
      placeholder (half and half) kept so fit checks have a number, and the UI
      must present it as unknown rather than as telemetry.
    """
    from app.services.grading_service import is_antigravity_model

    if is_antigravity_model(model_name):
        return {
            "capacity_gb": 0.0,
            "capacity_mb": 0.0,
            "available_gb": 0.0,
            "available_mb": 0.0,
            "used_gb": 0.0,
            "used_mb": 0.0,
            "model_vram_bytes": 0,
            "model_vram_gb": 0.0,
            "model_approx_gb": 0.0,
            "model_loaded": False,
            "model_name": model_name,
            "gpu_name": "Antigravity Subscription (Cloud)",
            "is_unified_memory": False,
            "memory_source": "cloud",
            "usage_measured": False,
        }

    total_mb: float | None = None
    used_mb: float | None = None
    free_mb: float | None = None
    gpu_name: str | None = None
    is_unified = False
    memory_source = "system-ram"
    usage_measured = False

    # 1. Query NVIDIA SMI if available
    if shutil.which("nvidia-smi"):
        try:
            raw = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
                text=True,
                timeout=1.5,
            ).strip()
            if raw:
                first_line = raw.split("\n")[0]
                parts = [p.strip() for p in first_line.split(",")]
                gpu_name = parts[0]
                total_mb = float(parts[1])
                used_mb = float(parts[2])
                free_mb = float(parts[3])
                memory_source = "nvidia-smi"
                usage_measured = True
        except Exception as exc:
            log.debug("nvidia-smi live query failed: %s", exc)

    # 2. Apple Silicon unified memory
    if total_mb is None and platform.system() == "Darwin" and platform.machine() == "arm64":
        is_unified = True
        gpu_name = "Apple Silicon Integrated GPU (Metal)"
        ram_gb = _get_ram_gb()
        total_mb = ram_gb * 1024.0
        memory_source = "apple-unified"
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "vm.page_free_count", "vm.page_speculative_count"],
                text=True,
                timeout=1.5,
            )
            free_pages = sum(int(p.strip()) for p in out.strip().split() if p.strip().isdigit())
            free_mb = round((free_pages * 4096) / (1024 * 1024), 1)
            used_mb = max(0.0, total_mb - free_mb)
            usage_measured = True
        except Exception:
            free_mb = round(total_mb * 0.5, 1)
            used_mb = round(total_mb * 0.5, 1)

    # 3. Windows CIM fallback
    if total_mb is None and platform.system() == "Windows":
        try:
            detected_gpu, detected_vram_gb, _ = _get_gpu_info()
            if detected_vram_gb:
                gpu_name = detected_gpu
                total_mb = detected_vram_gb * 1024.0
                memory_source = "gpu-adapter"
                free_mb = round(total_mb * 0.5, 1)
                used_mb = round(total_mb * 0.5, 1)
        except Exception:
            pass

    # 4. Host RAM fallback
    if total_mb is None:
        ram_gb = _get_ram_gb()
        total_mb = ram_gb * 1024.0
        free_mb = round(ram_gb * 1024.0 * 0.5, 1)
        used_mb = round(ram_gb * 1024.0 * 0.5, 1)

    # 5. Query Ollama /api/ps for currently running models in VRAM
    model_loaded = False
    model_vram_bytes = 0
    try:
        import httpx

        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{ollama_base_url}/api/ps")
            if resp.status_code == 200:
                ps_models = resp.json().get("models", [])
                for pm in ps_models:
                    pm_name = (pm.get("name") or pm.get("model") or "").lower()
                    if model_name:
                        mn_clean = model_name.lower().split(":")[0]
                        if mn_clean in pm_name or pm_name in model_name.lower():
                            model_loaded = True
                            model_vram_bytes = pm.get("size_vram") or pm.get("size") or 0
                            break
                    elif ps_models:
                        model_loaded = True
                        model_vram_bytes = pm.get("size_vram") or pm.get("size") or 0
                        break
    except Exception as exc:
        log.debug("Ollama /api/ps check failed: %s", exc)

    # Calculate approximate footprint based on model size
    approx_gb = 4.7
    if model_name:
        mn = model_name.lower()
        if "9b" in mn:
            approx_gb = 5.3
        elif "7b" in mn:
            approx_gb = 4.7
        elif any(k in mn for k in ("4b", "e4b", "gemma", "3b")):
            approx_gb = 2.5
        elif "1.5b" in mn:
            approx_gb = 1.2

    capacity_gb = round(total_mb / 1024.0, 2) if total_mb else 0.0
    available_gb = round(free_mb / 1024.0, 2) if free_mb else 0.0
    used_gb = round(used_mb / 1024.0, 2) if used_mb else 0.0
    model_vram_gb = round(model_vram_bytes / (1024.0**3), 2) if model_vram_bytes else 0.0

    return {
        "capacity_gb": capacity_gb,
        "capacity_mb": round(total_mb, 1) if total_mb else 0.0,
        "available_gb": available_gb,
        "available_mb": round(free_mb, 1) if free_mb else 0.0,
        "used_gb": used_gb,
        "used_mb": round(used_mb, 1) if used_mb else 0.0,
        "model_vram_bytes": model_vram_bytes if model_loaded else 0,
        "model_vram_gb": model_vram_gb,
        "model_approx_gb": approx_gb,
        "model_loaded": model_loaded,
        "model_name": model_name,
        "gpu_name": gpu_name or "Graphics Processor",
        "is_unified_memory": is_unified,
        "memory_source": memory_source,
        "usage_measured": usage_measured,
    }
