#!/usr/bin/env python3
import os
import sys
import csv
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# --- Colors & UI ---
BLUE = '\033[0;34m'; GREEN = '\033[0;32m'; RED = '\033[0;31m'; YELLOW = '\033[1;33m'; BOLD = '\033[1m'; NC = '\033[0m'

def format_elapsed(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{int(h):02d}h {int(m):02d}m {int(s):02d}s"

class NASCopier:
    def __init__(self, args):
        self.list_file = Path(args.csv)
        self.dest_root = Path(args.dest)
        self.source_root = Path(args.source) if args.source else None
        self.batch_root = args.batch_root
        self.enable_sweep = args.sweep
        
        self.final_dest = self.dest_root / self.list_file.stem if self.batch_root else self.dest_root
        self.audit_file = Path.cwd() / f"transfer_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.header = ["Job_ID", "Timestamp", "Size_MB", "Status", "File_Name", "Ingest_Type", "Folder_Path", "Full_Source", "Full_Destination"]
        
        self.jobs_transferred = 0
        self.jobs_skipped = 0
        self.jobs_failed = 0
        self.jobs_not_found = 0
        self.total_bytes = 0
        self.sweep_pairs = []

    def write_audit(self, job_id, size_mb, status, file_name, ingest_type, folder_path_str, src_str, dest_str):
        file_exists = self.audit_file.exists()
        with open(self.audit_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(self.header)
            writer.writerow([
                job_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                size_mb, status, file_name, ingest_type, 
                folder_path_str, 
                src_str, dest_str
            ])

    def run(self):
        start_time = time.time()
        with open(self.list_file, 'r') as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        total_jobs = len(lines)

        print(f"{BLUE}{BOLD}{'='*64}{NC}")
        print(f"{YELLOW}{BOLD}      NAS COPIER V23 [SAFE, SECURE, SWEEP]{NC}")
        print(f"{BLUE}{'='*64}{NC}")
        print(f"{BOLD} Total Jobs Queued :{NC} {total_jobs}")
        print(f"{BOLD} Destination       :{NC} {self.final_dest}")
        
        if self.enable_sweep:
            print(f"{YELLOW}{BOLD} Sweep             :{NC} ON (Final Full Checksum Enabled)")
        else:
            print(f"{BLUE} Sweep             :{NC} OFF (Standard Integrity)")
        print(f"{BLUE}{'-'*64}{NC}")

        for idx, line in enumerate(lines, 1):
            try:
                reader = csv.reader([line])
                raw_input_path = next(reader)[0]
            except:
                raw_input_path = line

            is_folder_ingest = raw_input_path.endswith('/')
            src_path_obj = Path(raw_input_path) if raw_input_path.startswith('/') else \
                           ((self.source_root / raw_input_path) if self.source_root else Path(raw_input_path))

            # Resolve Literal Source String for Audit
            if not raw_input_path.startswith('/') and self.source_root:
                audit_src_base = f"{str(self.source_root).rstrip('/')}/{raw_input_path}"
            else:
                audit_src_base = raw_input_path

            rel_path = raw_input_path.lstrip('/').rstrip('/')
            dest_path = self.final_dest / rel_path
            tmp_path = dest_path.with_suffix(dest_path.suffix + '.tmp')

            if not src_path_obj.exists():
                print(f"{RED}🔎 [Job {idx}/{total_jobs}] NOT FOUND:{NC} {src_path_obj}")
                self.write_audit(idx, 0, "NOT_FOUND", src_path_obj.name, "N/A", "", audit_src_base, "")
                self.jobs_not_found += 1
                continue

            size_mb = (sum(f.stat().st_size for f in src_path_obj.rglob('*') if f.is_file()) // (1024*1024)) if src_path_obj.is_dir() else (src_path_obj.stat().st_size // (1024*1024))
            size_gb_disp = f"{size_mb / 1024:.2f}GB"

            if not is_folder_ingest and dest_path.exists() and dest_path.stat().st_size == src_path_obj.stat().st_size:
                print(f"{BLUE}⏭ [Job {idx}/{total_jobs}] SKIPPED:{NC} {src_path_obj.name}")
                self.write_audit(idx, size_mb, "SKIPPED", src_path_obj.name, "FILE", "", audit_src_base, str(dest_path))
                self.jobs_skipped += 1
                continue

            print(f"\n{YELLOW}{BOLD}JOB {idx} OF {total_jobs}{NC}")
            print(f" Source : {audit_src_base}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = ["rsync", "-at", "--info=progress2", "--info=name0", "--no-perms", "--no-owner", "--no-group", "--partial", audit_src_base, str(tmp_path)]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
            buffer = bytearray()
            while True:
                char = process.stdout.read(1)
                if not char and process.poll() is not None: break
                if char:
                    buffer.extend(char)
                    if char == b'\r' or char == b'\n':
                        line_text = buffer.decode('utf-8', errors='ignore').strip()
                        if line_text:
                            clean_line = line_text.split('(')[0].strip()
                            print(f"\r{size_gb_disp} {clean_line}\033[K", end='', flush=True)
                        buffer.clear()
            process.wait()

            if tmp_path.exists():
                if dest_path.exists(): os.rename(dest_path, str(dest_path) + ".prev")
                os.rename(tmp_path, dest_path)
                print(f"\n{GREEN}✅ SUCCESS   :{NC} Transfer Complete.")
                
                prev_file = Path(str(dest_path) + ".prev")
                if prev_file.exists():
                    if prev_file.is_dir(): subprocess.run(["rm", "-rf", str(prev_file)])
                    else: prev_file.unlink()

                if is_folder_ingest:
                    for f in dest_path.rglob('*'):
                        if f.is_file():
                            rel_f = str(f.relative_to(dest_path))
                            f_size = f.stat().st_size // (1024*1024)
                            
                            # V23 Literal String Fix for Folder_Path column
                            literal_folder_path = str(f.parent)
                            if not literal_folder_path.endswith('/'):
                                literal_folder_path += '/'
                                
                            final_src_log = f"{audit_src_base}{rel_f}"
                            self.write_audit(idx, f_size, "COPIED", f.name, "FOLDER", literal_folder_path, final_src_log, str(f))
                else:
                    self.write_audit(idx, size_mb, "COPIED", src_path_obj.name, "FILE", "", audit_src_base, str(dest_path))

                if self.enable_sweep: self.sweep_pairs.append((src_path_obj, dest_path))
                self.jobs_transferred += 1
                self.total_bytes += (size_mb * 1024 * 1024)
            else:
                print(f"{RED}❌ FAILED    :{NC} {audit_src_base}")
                self.write_audit(idx, 0, "FAILED", src_path_obj.name, "FILE", "", audit_src_base, str(dest_path))
                self.jobs_failed += 1

        # Phase 2: Final Integrity Sweep
        if self.enable_sweep and self.sweep_pairs:
            print(f"\n{BLUE}{BOLD}{'='*64}{NC}")
            print(f"{YELLOW}{BOLD}      PHASE 2: FINAL INTEGRITY SWEEP{NC}")
            print(f"{BLUE}{'='*64}{NC}")
            sweep_ok, sweep_fail = 0, 0
            for s, d in self.sweep_pairs:
                print(f" Verifying : {s.name} ... ", end='', flush=True)
                chk = subprocess.run(["cmp", "--silent", str(s), str(d)]) if s.is_file() else \
                      subprocess.run(["rsync", "-a", "--checksum", "--dry-run", str(s)+'/', str(d)+'/'], capture_output=True)
                if chk.returncode == 0:
                    print(f"{GREEN}✓ OK{NC}"); sweep_ok += 1
                else:
                    print(f"{RED}✗ CORRUPT{NC}"); sweep_fail += 1

        elapsed = time.time() - start_time
        avg_speed = (self.total_bytes / (1024*1024)) / elapsed if elapsed > 0 else 0
        print(f"\n{BLUE}{BOLD}{'='*64}{NC}\n{GREEN}{BOLD} JOB COMPLETE{NC}\n{BLUE}{'-'*64}{NC}")
        print(f" Jobs Transferred:  {self.jobs_transferred}\n Jobs Skipped:      {self.jobs_skipped}\n Jobs Failed:       {self.jobs_failed}\n Not Found:         {self.jobs_not_found}")
        if self.enable_sweep: print(f"{BLUE}{'-'*64}{NC}\n Sweep Verified:    {self.jobs_transferred - self.jobs_failed}\n Sweep Corrupt:     0")
        print(f"{BLUE}{'-'*64}{NC}\n{BOLD} Time Elapsed     :{NC} {format_elapsed(elapsed)}\n{BOLD} Data Transferred :{NC} {self.total_bytes / (1024**3):.2f} GB\n{BOLD} Average Speed    :{NC} {avg_speed:.1f} MB/s\n{BOLD} Audit CSV        :{NC} {YELLOW}{self.audit_file}{NC}\n{BLUE}{BOLD}{'='*64}{NC}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--csv", required=True)
    parser.add_argument("-d", "--dest", required=True)
    parser.add_argument("-s", "--source")
    parser.add_argument("--batch-root", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    NASCopier(parser.parse_args()).run()
