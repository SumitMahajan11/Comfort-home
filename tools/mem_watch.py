"""
tools/mem_watch.py

Monitors system and process memory usage every N seconds (default: 5 s)
and appends telemetry rows to reports/mem_trace.csv.

Columns recorded:
- timestamp: ISO 8601 local timestamp
- avail_ram_gb: Available physical RAM (GB)
- used_ram_gb: Used physical RAM (GB)
- total_ram_gb: Total physical RAM (GB)
- committed_gb: Total committed bytes across RAM + Pagefile (GB) via GlobalMemoryStatusEx
- commit_limit_gb: System commit limit (GB) via GlobalMemoryStatusEx
- commit_avail_gb: Available commit space before paging failure (GB)
- python_rss_gb: Summed RSS of all running python.exe processes (GB)
- python_proc_count: Number of running python.exe processes
- disk_free_c_gb: Free disk space on C: (GB)
- disk_free_d_gb: Free disk space on D: (GB)
"""

import os
import sys
import time
import shutil
import ctypes
import argparse
import datetime
import psutil
import pandas as pd

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
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]
    def __init__(self):
        self.dwLength = ctypes.sizeof(self)
        super().__init__()

def get_commit_status():
    stat = MEMORYSTATUSEX()
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    commit_limit = stat.ullTotalPageFile
    avail_pagefile = stat.ullAvailPageFile
    committed_bytes = commit_limit - avail_pagefile
    return (
        round(committed_bytes / (1024**3), 3),
        round(commit_limit / (1024**3), 3),
        round(avail_pagefile / (1024**3), 3)
    )

def sample_memory():
    vm = psutil.virtual_memory()
    avail_ram = round(vm.available / (1024**3), 3)
    used_ram = round(vm.used / (1024**3), 3)
    total_ram = round(vm.total / (1024**3), 3)
    
    committed_gb, commit_limit_gb, commit_avail_gb = get_commit_status()
    
    # Python process stats
    py_rss_total = 0
    py_count = 0
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            if 'python' in (p.info['name'] or '').lower():
                py_count += 1
                py_rss_total += p.info['memory_info'].rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    py_rss_gb = round(py_rss_total / (1024**3), 3)
    
    # Disk space
    try:
        c_free = round(shutil.disk_usage("C:\\").free / (1024**3), 2)
    except Exception:
        c_free = 0.0
    try:
        d_free = round(shutil.disk_usage("D:\\").free / (1024**3), 2)
    except Exception:
        d_free = 0.0
        
    return {
        'timestamp': datetime.datetime.now().isoformat(),
        'avail_ram_gb': avail_ram,
        'used_ram_gb': used_ram,
        'total_ram_gb': total_ram,
        'committed_gb': committed_gb,
        'commit_limit_gb': commit_limit_gb,
        'commit_avail_gb': commit_avail_gb,
        'python_rss_gb': py_rss_gb,
        'python_proc_count': py_count,
        'disk_free_c_gb': c_free,
        'disk_free_d_gb': d_free
    }

def main():
    parser = argparse.ArgumentParser(description="Memory Watcher for ClimateAdapt-Comfort")
    parser.add_argument("--interval", type=float, default=5.0, help="Sampling interval in seconds")
    parser.add_argument("--duration", type=float, default=None, help="Total duration to run in seconds (default: infinite)")
    parser.add_argument("--output-csv", default="reports/mem_trace.csv", help="Destination CSV path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output_csv)), exist_ok=True)
    print(f"Starting mem_watch (interval={args.interval}s, duration={args.duration}s) -> {args.output_csv}")
    
    t_start = time.time()
    while True:
        record = sample_memory()
        df_row = pd.DataFrame([record])
        if not os.path.exists(args.output_csv):
            df_row.to_csv(args.output_csv, index=False)
        else:
            df_row.to_csv(args.output_csv, mode='a', header=False, index=False)
            
        print(f"[{record['timestamp']}] Avail RAM: {record['avail_ram_gb']:.2f}GB | Commit: {record['committed_gb']:.2f}/{record['commit_limit_gb']:.2f}GB | Py RSS ({record['python_proc_count']} procs): {record['python_rss_gb']:.2f}GB | C: {record['disk_free_c_gb']}GB, D: {record['disk_free_d_gb']}GB")
        
        if args.duration is not None and (time.time() - t_start + args.interval > args.duration):
            break
            
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
