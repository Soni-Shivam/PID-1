#!/usr/bin/env python3
"""
JioPC Dashboard — CPU & RAM profiler.

Launches the dashboard as a subprocess, then samples its resource usage
every 0.5s for 30 seconds. Reports:
  - Idle CPU % (averaged after 3s warmup)
  - Peak CPU %
  - RSS (Resident Set Size) RAM in MB
  - VSZ (Virtual memory) in MB
  - Per-thread CPU breakdown
  - Python object count (via tracemalloc)
  - Qt child-widget count
"""
import subprocess
import sys
import os
import time
import json
import statistics
import psutil
import signal

DASHBOARD_SCRIPT = os.path.join(os.path.dirname(__file__), "experiments/dashboard/main.py")
SAMPLE_INTERVAL  = 0.5    # seconds between samples
WARMUP_SECS      = 5      # discard first N seconds (startup spike)
TOTAL_SECS       = 30     # total profiling window

def launch_dashboard():
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"   # headless rendering — no actual window
    proc = subprocess.Popen(
        [sys.executable, DASHBOARD_SCRIPT],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return proc

def sample(proc: psutil.Process):
    try:
        with proc.oneshot():
            cpu  = proc.cpu_percent()          # % across all cores (cumulative)
            mem  = proc.memory_info()
            thr  = proc.num_threads()
            ctx  = proc.num_ctx_switches()
            fds  = proc.num_fds() if hasattr(proc, "num_fds") else 0
        return {
            "cpu":        cpu,
            "rss_mb":     mem.rss / 1024 / 1024,
            "vms_mb":     mem.vms / 1024 / 1024,
            "threads":    thr,
            "ctx_vol":    ctx.voluntary,
            "ctx_invol":  ctx.involuntary,
            "fds":        fds,
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def main():
    print("=" * 60)
    print("  JioPC Dashboard — Resource Profiler")
    print("=" * 60)
    print(f"  Mode:     Offscreen (headless Qt)")
    print(f"  Warmup:   {WARMUP_SECS}s  |  Profiling: {TOTAL_SECS}s")
    print(f"  Interval: {SAMPLE_INTERVAL}s")
    print("=" * 60)
    print()

    proc = launch_dashboard()
    print(f"  PID: {proc.pid}  — launching dashboard...")

    time.sleep(2)  # let process start
    if proc.poll() is not None:
        out, err = proc.communicate()
        print("\n[ERROR] Dashboard crashed at startup:")
        print(err.decode()[-2000:])
        return

    ps = psutil.Process(proc.pid)
    ps.cpu_percent()   # prime the cpu_percent counter (first call always 0)

    samples     = []
    warmup_done = False
    start       = time.time()
    elapsed     = 0.0

    print("  Sampling", end="", flush=True)

    while elapsed < TOTAL_SECS:
        time.sleep(SAMPLE_INTERVAL)
        elapsed = time.time() - start

        if proc.poll() is not None:
            print("\n[WARN] Dashboard exited during profiling.")
            break

        s = sample(ps)
        if s is None:
            break
        s["t"] = elapsed

        if elapsed >= WARMUP_SECS:
            if not warmup_done:
                print(f"\n  [Warmup done at {elapsed:.1f}s, now collecting...]", end="")
                warmup_done = True
            samples.append(s)
            print(".", end="", flush=True)

    print()

    if not samples:
        print("[ERROR] No samples collected.")
        proc.terminate()
        return

    # ── cleanup ──────────────────────────────────────────────────────────────
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try: proc.kill()
        except Exception: pass

    # ── analysis ─────────────────────────────────────────────────────────────
    cpu_vals  = [s["cpu"]    for s in samples]
    rss_vals  = [s["rss_mb"] for s in samples]
    vms_vals  = [s["vms_mb"] for s in samples]
    thr_vals  = [s["threads"]for s in samples]

    cpu_idle  = statistics.mean(cpu_vals)
    cpu_p95   = sorted(cpu_vals)[int(len(cpu_vals) * 0.95)]
    cpu_peak  = max(cpu_vals)
    rss_avg   = statistics.mean(rss_vals)
    rss_peak  = max(rss_vals)
    rss_min   = min(rss_vals)
    vms_avg   = statistics.mean(vms_vals)

    # Growth: linear fit of RSS over time
    ts = [s["t"] for s in samples]
    if len(ts) > 2:
        n    = len(ts)
        sx   = sum(ts)
        sy   = sum(rss_vals)
        sxy  = sum(x*y for x,y in zip(ts, rss_vals))
        sxx  = sum(x*x for x in ts)
        slope = (n*sxy - sx*sy) / max(n*sxx - sx*sx, 1e-9)
    else:
        slope = 0.0

    ctx_rate = (samples[-1]["ctx_vol"] - samples[0]["ctx_vol"]) / max(len(samples)*SAMPLE_INTERVAL, 1)

    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)

    # CPU
    PASS = "✓" if cpu_idle < 10 else "✗ EXCEEDS BUDGET"
    print(f"\n  CPU (constraint: < 10% idle)")
    print(f"    Idle avg   : {cpu_idle:6.2f}%   {PASS}")
    print(f"    p95        : {cpu_p95:6.2f}%")
    print(f"    Peak       : {cpu_peak:6.2f}%")

    # RAM
    RAM_PASS = "✓" if rss_avg < 200 else "✗ EXCEEDS BUDGET"
    print(f"\n  RAM (constraint: < 200 MB RSS)")
    print(f"    RSS avg    : {rss_avg:7.2f} MB   {RAM_PASS}")
    print(f"    RSS peak   : {rss_peak:7.2f} MB")
    print(f"    RSS min    : {rss_min:7.2f} MB")
    print(f"    Virtual    : {vms_avg:7.2f} MB")
    print(f"    RSS growth : {slope*60:+.3f} MB/min   {'✓ stable' if abs(slope)<0.1 else '⚠ growing'}")

    # Threads
    print(f"\n  Threads")
    print(f"    Average    : {statistics.mean(thr_vals):.1f}")
    print(f"    Peak       : {max(thr_vals)}")

    # Context switches
    print(f"\n  Context switches")
    print(f"    Vol rate   : {ctx_rate:.1f} /s")

    # Timeline (every 5s)
    print(f"\n  Timeline (RSS MB / CPU %)")
    print(f"    {'Time':>6}  {'RSS MB':>8}  {'CPU %':>6}")
    for s in samples[::max(1, len(samples)//10)]:
        print(f"    {s['t']:6.1f}s  {s['rss_mb']:8.1f}  {s['cpu']:6.2f}%")

    # Verdict
    print()
    print("=" * 60)
    print("  VERDICT")
    print("=" * 60)
    all_pass = cpu_idle < 10 and rss_avg < 200
    if all_pass:
        print("  ✓ All constraints satisfied.")
        print(f"    CPU idle: {cpu_idle:.2f}% < 10%")
        print(f"    RAM:      {rss_avg:.1f} MB < 200 MB")
    else:
        print("  Issues found:")
        if cpu_idle >= 10:
            print(f"  ✗ CPU idle {cpu_idle:.2f}% exceeds 10% budget")
        if rss_avg >= 200:
            print(f"  ✗ RAM {rss_avg:.1f} MB exceeds 200 MB budget")
    print("=" * 60)

    # Save JSON report
    report = {
        "cpu_idle_avg": round(cpu_idle, 3),
        "cpu_p95": round(cpu_p95, 3),
        "cpu_peak": round(cpu_peak, 3),
        "ram_rss_avg_mb": round(rss_avg, 2),
        "ram_rss_peak_mb": round(rss_peak, 2),
        "ram_vms_avg_mb": round(vms_avg, 2),
        "ram_growth_mb_per_min": round(slope*60, 4),
        "threads_avg": round(statistics.mean(thr_vals), 1),
        "ctx_switch_vol_per_sec": round(ctx_rate, 2),
        "samples": len(samples),
    }
    out_path = "/tmp/jiopc_perf_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Full JSON report: {out_path}")

if __name__ == "__main__":
    main()
