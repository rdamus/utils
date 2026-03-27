#!/usr/bin/env zsh

# Default log file
LOG_FILE="transfer_log.txt"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -l|--list) LIST_FILE="$2"; shift ;;
        -s|--source) SOURCE_DIR="$2"; shift ;;
        -d|--dest) DEST_DIR="$2"; shift ;;
        --log) LOG_FILE="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Validate required arguments
if [[ -z "$LIST_FILE" || -z "$SOURCE_DIR" || -z "$DEST_DIR" ]]; then
    echo "Usage: ./nas_copier.sh -l <list_file> -s <source_dir> -d <dest_dir> [--log <log_file>]"
    exit 1
fi

if [[ ! -f "$LIST_FILE" ]]; then
    echo "ERROR: The list file '$LIST_FILE' does not exist."
    exit 1
fi

# Create NAS destination root if it doesn't exist
if [[ ! -d "$DEST_DIR" ]]; then
    echo "WARNING: NAS destination '$DEST_DIR' does not exist. Creating it now."
    mkdir -p "$DEST_DIR"
fi

# Function to get file size across Mac (stat -f%z) and Linux (stat -c%s)
get_size() {
    stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null
}

echo "\nLoaded paths from $LIST_FILE"
echo "Scanning source drive: $SOURCE_DIR\n"
echo "--- Starting NAS Copy Job ---" >> "$LOG_FILE"

# Read the file line by line
while IFS= read -r path_str || [[ -n "$path_str" ]]; do
    # Skip empty lines
    [[ -z "${path_str// /}" ]] && continue

    # Strip leading slashes to make it a clean relative path
    clean_path="${path_str#/}"
    while [[ "$clean_path" == /* ]]; do clean_path="${clean_path#/}"; done

    src_file="$SOURCE_DIR/$clean_path"
    dest_file="$DEST_DIR/$clean_path"
    dest_parent="${dest_file%/*}"

    if [[ -f "$src_file" ]]; then
        # --- Check if file exists and matches size ---
        if [[ -f "$dest_file" ]]; then
            src_size=$(get_size "$src_file")
            dest_size=$(get_size "$dest_file")
            
            if [[ "$src_size" == "$dest_size" ]]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - SKIPPED (Already on NAS): $path_str" >> "$LOG_FILE"
                echo "⏭️  Skipped: $path_str (Already exists)"
                continue
            fi
        fi

        # Create destination directory structure
        mkdir -p "$dest_parent"

        # Copy using rsync: 
        # -a (archive, preserves metadata)
        # --info=progress2 (shows overall progress/speed similar to tqdm)
        if rsync -a --info=progress2 "$src_file" "$dest_file"; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - COPIED: $path_str" >> "$LOG_FILE"
            echo "✅ Success: $path_str"
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - FAILED TO COPY: $path_str" >> "$LOG_FILE"
            echo "❌ Failed:  $path_str (See log for details)"
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - DEBUG - NOT FOUND on this drive: $path_str" >> "$LOG_FILE"
    fi

done < "$LIST_FILE"

echo "--- Job Complete ---" >> "$LOG_FILE"
echo "\n🎉 All done! Check $LOG_FILE for a full record."
