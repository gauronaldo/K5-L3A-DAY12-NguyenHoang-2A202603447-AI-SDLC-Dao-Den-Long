"""Process memory / start time / OS description without third-party packages (Windows, Linux, macOS)."""
import os
import platform
import subprocess
import sys
import time

_IMPORT_TIME = time.time()


def rss_mb():
    """Current resident set size in MB."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return pmc.WorkingSetSize / 1048576.0
    if os.path.exists("/proc/self/statm"):
        with open("/proc/self/statm") as f:
            pages = int(f.read().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE") / 1048576.0
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True).stdout
    return int(out.strip() or 0) / 1024.0


def process_start_epoch():
    """When the OS created this process (seconds since epoch); falls back to module import time."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            ft = [wintypes.FILETIME() for _ in range(4)]
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            k32.GetProcessTimes(k32.GetCurrentProcess(), *[ctypes.byref(f) for f in ft])
            t = (ft[0].dwHighDateTime << 32) | ft[0].dwLowDateTime
            return t / 1e7 - 11644473600.0
        if os.path.exists("/proc/self/stat"):
            with open("/proc/self/stat") as f:
                start_ticks = int(f.read().rsplit(")", 1)[1].split()[19])
            with open("/proc/stat") as f:
                btime = int(next(l for l in f if l.startswith("btime")).split()[1])
            return btime + start_ticks / os.sysconf("SC_CLK_TCK")
    except Exception:
        pass
    return _IMPORT_TIME


def os_description():
    system, release = platform.system(), platform.release()
    if system == "Windows":   # platform.release() says "10" on Windows 11; the build number tells them apart
        build = int(platform.version().split(".")[-1] or 0)
        release = "11" if build >= 22000 else release
        release += " (build %d)" % build
    elif system == "Darwin":
        release = "macOS " + platform.mac_ver()[0]
    return "%s %s (%s), Python %s" % (system, release, platform.machine(), platform.python_version())
