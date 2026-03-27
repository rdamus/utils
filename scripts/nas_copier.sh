#!/usr/bin/env zsh

# Default log file
LOG_FILE="transfer_log.txt"
SOURCE_DIR=""

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
if [[ -z "$LIST_FILE" || -z "$DEST_DIR" ]]; then
    echo "Usage: ./nas_copier.sh -l <list_file.txt|.csv> -d <dest_dir> [-s <source_dir>] [--log <log_file>]"
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
if [[ -n "$SOURCE_DIR" ]]; then
    echo "Using base source directory: $SOURCE_DIR"
else
    echo "No source directory provided. Treating paths in list as absolute."
fi
echo "\n--- Starting NAS Copy Job ---" >> "$LOG_FILE"

# Initialize counters for the summary
count_copied=0
count_skipped=0
count_failed=0
count_not_found=0

# Read the file line by line
while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    # 1. Strip hidden carriage returns (common in Windows-generated CSVs)
    path_str="${raw_line%$'\r'}"
    
    # 2. Strip surrounding double quotes (common in CSVs if paths have spaces)
    if [[ "$path_str" == \"*\" ]]; then
        path_str="${path_str:1:-1}"
    fi

    # Skip empty lines
    [[ -z "${path_str// /}" ]] && continue

    # Strip leading slashes to make a clean relative path for the DESTINATION structure
    clean_path="${path_str}"
    while [[ "$clean_path" == /* ]]; do clean_path="${clean_path#/}"; done

    # Determine the source file based on whether -s was provided
    if [[ -n "$SOURCE_DIR" ]]; then
        src_file="$SOURCE_DIR/$clean_path"
    else
        src_file="$path_str"
    fi
    
    dest_file="$DEST_DIR/$clean_path"
    dest_parent="${dest_file%/*}"

    if [[ -f "$src_file" ]]; then
        # --- Check if file exists and matches size ---
        if [[ -f "$dest_file" ]]; then
            src_size=$(get_size "$src_file")
            dest_size=$(get_size "$dest_file")
            
            if [[ "$src_size" == "$dest_size" ]]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - SKIPPED (Already on NAS): $src_file" >> "$LOG_FILE"
                echo "⏭️  Skipped: $src_file (Already exists)"
                ((count_skipped++))
                continue
            fi
        fi

        # Create destination directory structure
        mkdir -p "$dest_parent"

        # Copy using rsync
        if rsync -a --info=progress2 "$src_file" "$dest_file"; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - COPIED: $src_file" >> "$LOG_FILE"
            echo "✅ Success: $src_file"
            ((count_copied++))
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - FAILED TO COPY: $src_file" >> "$LOG_FILE"
            echo "❌ Failed:  $src_file (See log for details)"
            ((count_failed++))
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - DEBUG - NOT FOUND: $src_file" >> "$LOG_FILE"
        ((count_not_found++))
    fi

done < "$LIST_FILE"

# Log and print the final summary
echo "--- Job Complete ---" >> "$LOG_FILE"
echo "Summary: $count_copied copied, $count_skipped skipped, $count_failed failed, $count_not_found not found on this drive." >> "$LOG_FILE"

echo "\n🎉 All done! Here is your summary:"
echo "-----------------------------------"
echo "✅ Copied:    $count_copied"
echo "⏭️  Skipped:   $count_skipped"
echo "❌ Failed:    $count_failed"
echo "🔍 Not Found: $count_not_found (Check next drive)"
echo "-----------------------------------"
echo "Check $LOG_FILE for a full record."
