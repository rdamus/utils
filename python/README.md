# Python Utilities


This is a solid script! Version 23 looks like a professional-grade tool, especially with the rsync integration and that secondary integrity sweep. Using `.tmp` extensions for atomic writes is a great touch for NAS environments where network interruptions are a common headache.

Here is a clean, professional **README.md** tailored for your GitHub repository.

---

# NAS Copier

**NAS Copier v1.23** is a robust Python-based data migration tool designed for safe, secure, and auditable file transfers. Built specifically for high-volume environments, it leverages `rsync` for performance and adds a secondary "Sweep" phase to ensure 100% data integrity via checksum verification.

## Installation

There is no `pip` command needed for installation.  See requirements below.


## 🚀 Key Features

* **Atomic Transfers:** Files are copied with a `.tmp` extension and renamed only upon successful completion to prevent partial or corrupted files.
* **Intelligent Skipping:** Automatically detects and skips files that already exist at the destination with matching sizes.
* **Phase 2 Integrity Sweep:** An optional post-transfer verification phase that performs a full bit-for-bit comparison (`cmp`) or rsync checksum check.
* **Comprehensive Auditing:** Every job is logged to a timestamped CSV file containing sizes, status (COPIED, SKIPPED, FAILED), and full path metadata.
* **Progress Tracking:** Real-time terminal UI with color-coded status updates and transfer speeds.

---

## 🛠 Command Line Options

| Option | Short | Description |
| :--- | :--- | :--- |
| `--csv` | `-c` | **Required.** Path to the CSV/text file containing the list of files or folders to copy. |
| `--dest` | `-d` | **Required.** The root destination directory where files will be moved. |
| `--source` | `-s` | Optional. A base source path to prepend to relative paths found in your CSV. |
| `--batch-root`| N/A | If set, creates a subfolder in the destination named after your CSV file. |
| `--sweep` | N/A | Enables "Phase 2," performing a post-copy checksum verification on all items. |

---

## 📖 Usage Examples

### 1. Basic Transfer
Copy items listed in `manifest.csv` to a backup drive.
```bash
python3 nas_copier.py -c manifest.csv -d /Volumes/Backup_NAS/
```

### 2. Standard Migration with Source Root
If your CSV contains relative paths (e.g., `folder/file.mxf`), use `-s` to define the starting point.
```bash
python3 nas_copier.py -c list.csv -s /Volumes/Production_Drive/ -d /Volumes/Archive/
```

### 3. Maximum Security (Batch & Sweep)
This creates a dedicated folder for the job and runs a full bit-for-bit verification after the transfer is complete.
```bash
python3 nas_copier.py -c daily_ingest.csv -d /Volumes/NAS/ --batch-root --sweep
```

---

## 📊 Audit Logging
The script generates a detailed audit trail for every session. The log file is named `transfer_audit_YYYYMMDD_HHMMSS.csv` and includes:
* **Job ID & Timestamp:** When the specific item was processed.
* **Size (MB):** The footprint of the transferred data.
* **Status:** `COPIED`, `SKIPPED`, `FAILED`, or `NOT_FOUND`.
* **Pathing:** Full source and destination paths for easy troubleshooting.

---

## ⚙️ Requirements
* **OS:** Linux or macOS (Requires `rsync` and `cmp` binaries).
* **Python:** 3.6 or higher.
* **Permissions:** Ensure the user has read access to the source and write access to the destination.

