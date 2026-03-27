import argparse
import logging
import os
import shutil
from pathlib import Path
from tqdm import tqdm

def setup_logger(log_file_path):
    """Sets up a logger to write to both a file and the console."""
    logger = logging.getLogger("NASCopier")
    logger.setLevel(logging.INFO)
    
    fh = logging.FileHandler(log_file_path)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

def copy_with_progress(src, dst):
    """Copies a file in chunks while updating a progress bar, preserving metadata."""
    total_size = os.path.getsize(src)
    
    # Open source for reading, destination for writing, and setup the progress bar
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst, tqdm(
        total=total_size, 
        unit='B', 
        unit_scale=True, 
        unit_divisor=1024, 
        desc=f"Copying {Path(src).name}", 
        leave=False # Removes the bar when the individual file finishes
    ) as pbar:
        while True:
            # Read in 1MB chunks
            chunk = fsrc.read(1024 * 1024)
            if not chunk:
                break
            fdst.write(chunk)
            pbar.update(len(chunk))
            
    # Preserve original timestamps and metadata after copying the data
    shutil.copystat(src, dst)

def copy_files_to_nas(file_list_path, source_drive_path, nas_dest_path, logger):
    """Reads paths, checks if they exist, and copies to NAS with progress and skipping logic."""
    list_file = Path(file_list_path)
    source_root = Path(source_drive_path)
    nas_root = Path(nas_dest_path)

    if not list_file.exists():
        print(f"ERROR: The list file '{list_file}' does not exist.")
        return

    if not nas_root.exists():
        print(f"WARNING: NAS destination '{nas_root}' does not exist. Creating it now.")
        nas_root.mkdir(parents=True, exist_ok=True)

    with open(list_file, 'r', encoding='utf-8') as f:
        paths = [line.strip() for line in f if line.strip()]

    print(f"\nLoaded {len(paths)} paths from {list_file.name}")
    print(f"Scanning source drive: {source_root}\n")

    for path_str in paths:
        clean_path = path_str.lstrip('/\\')
        src_file = source_root / clean_path
        dest_file = nas_root / clean_path

        if src_file.exists() and src_file.is_file():
            # --- NEW: Check if file exists and matches size ---
            if dest_file.exists() and dest_file.is_file():
                if os.path.getsize(src_file) == os.path.getsize(dest_file):
                    logger.info(f"SKIPPED (Already on NAS): {path_str}")
                    print(f"⏭️  Skipped: {path_str} (Already exists)")
                    continue
            
            try:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Use our progress-tracking copy function
                copy_with_progress(src_file, dest_file)
                
                logger.info(f"COPIED: {path_str}")
                print(f"✅ Success: {path_str}")
            except Exception as e:
                logger.error(f"FAILED TO COPY: {path_str} | Error: {e}")
                print(f"❌ Failed:  {path_str} (See log for details)")
        else:
            logger.debug(f"NOT FOUND on this drive: {path_str}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy specific files from an external drive to a NAS with progress and skipping.")
    parser.add_argument("-l", "--list", required=True, help="Path to the text file containing paths to copy")
    parser.add_argument("-s", "--source", required=True, help="Root path of the currently mounted external drive")
    parser.add_argument("-d", "--dest", required=True, help="Root path of the NAS destination")
    parser.add_argument("--log", default="transfer_log.txt", help="Path to save the log file (default: transfer_log.txt)")
    
    args = parser.parse_args()
    
    logger = setup_logger(args.log)
    logger.info("--- Starting NAS Copy Job ---")
    
    copy_files_to_nas(args.list, args.source, args.dest, logger)
    
    logger.info("--- Job Complete ---")
    print("\n🎉 All done! Check transfer_log.txt for a full record of what was copied or skipped.")
