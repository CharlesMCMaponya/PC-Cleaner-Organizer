import os
import shutil
import hashlib
import argparse
import schedule
import time
import logging
import pathlib
import platform

# Set up logging to track what the script does
logging.basicConfig(
    filename='pc_cleaner.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define file types for organization (e.g., .jpg goes to Images)
FILE_CATEGORIES = {
    'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
    'Documents': ['.pdf', '.doc', '.docx', '.txt', '.xlsx'],
    'Videos': ['.mp4', '.mkv', '.avi'],
    'Music': ['.mp3', '.wav'],
    'Archives': ['.zip', '.rar', '.tar'],
    'Others': []  # For files that don’t match
}

# Define temp file locations for different operating systems
TEMP_DIRS = {
    'Windows': [os.path.expandvars(r'%temp%'), os.path.expandvars(r'%appdata%\Microsoft\Windows\Recent')],
    'Linux': ['/tmp', os.path.expanduser('~/.cache')],
    'Darwin': [os.path.expanduser('~/Library/Caches'), '/private/var/tmp']  # MacOS
}

def get_file_hash(file_path):
    """Calculate a unique code (hash) for a file to check if it’s a duplicate."""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.error(f"Error hashing {file_path}: {e}")
        return None

def organize_files(source_dir, delete_duplicates=False):
    """Move files to folders based on their type (e.g., .jpg to Images)."""
    if not os.path.exists(source_dir):
        logging.error(f"Directory {source_dir} does not exist.")
        print(f"Error: {source_dir} does not exist.")
        return 0, 0

    file_hashes = {}  # Track file hashes to find duplicates
    moved_count = 0
    duplicate_count = 0

    # Loop through files in the directory
    for filename in os.listdir(source_dir):
        source_path = os.path.join(source_dir, filename)
        if os.path.isfile(source_path):
            # Get file extension (e.g., .jpg)
            file_ext = os.path.splitext(filename)[1].lower()
            category = 'Others'  # Default folder
            for cat, exts in FILE_CATEGORIES.items():
                if file_ext in exts:
                    category = cat
                    break

            # Create the category folder (e.g., Images)
            category_dir = os.path.join(source_dir, category)
            os.makedirs(category_dir, exist_ok=True)

            # Check for duplicates
            if delete_duplicates:
                file_hash = get_file_hash(source_path)
                if file_hash and file_hash in file_hashes:
                    logging.warning(f"Duplicate found: {filename}. Deleting.")
                    os.remove(source_path)
                    duplicate_count += 1
                    continue
                if file_hash:
                    file_hashes[file_hash] = source_path

            # Move the file
            dest_path = os.path.join(category_dir, filename)
            if os.path.exists(dest_path):
                # Avoid overwriting by adding a number (e.g., file_1.jpg)
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(category_dir, f"{base}_{counter}{ext}")
                    counter += 1

            try:
                shutil.move(source_path, dest_path)
                logging.info(f"Moved {filename} to {category}")
                moved_count += 1
            except Exception as e:
                logging.error(f"Failed to move {filename}: {e}")
                print(f"Error moving {filename}: {e}")

    return moved_count, duplicate_count

def clean_temp_files():
    """Delete temporary files to free space."""
    system = platform.system()  # Detect OS (Windows, Linux, Mac)
    temp_dirs = TEMP_DIRS.get(system, [])
    deleted_count = 0
    total_size = 0

    # Warn user before deleting
    print("WARNING: This will delete temp files. It’s usually safe, but check pc_cleaner.log if issues arise.")
    confirm = input("Proceed? (y/n): ").lower()
    if confirm != 'y':
        print("Cleanup aborted.")
        return 0, 0

    # Loop through temp directories
    for temp_dir in temp_dirs:
        if not os.path.exists(temp_dir):
            continue
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_count += 1
                    total_size += file_size
                    logging.info(f"Deleted {file_path} ({file_size} bytes)")
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {e}")
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    shutil.rmtree(dir_path, ignore_errors=True)
                    logging.info(f"Deleted directory {dir_path}")
                except Exception as e:
                    logging.error(f"Failed to delete {dir_path}: {e}")

    return deleted_count, total_size

def run_automation(source_dir, delete_duplicates, clean_temp):
    """Run the organizer and/or cleaner."""
    logging.info("Starting PC cleaner and organizer.")
    moved_count = 0
    duplicate_count = 0
    deleted_count = 0
    total_size = 0

    if source_dir:
        moved_count, duplicate_count = organize_files(source_dir, delete_duplicates)
    if clean_temp:
        deleted_count, total_size = clean_temp_files()

    # Print and log a summary
    summary = (
        f"Summary:\n"
        f"- Moved {moved_count} files\n"
        f"- Deleted {duplicate_count} duplicates\n"
        f"- Deleted {deleted_count} temp files ({total_size / 1024:.2f} KB freed)"
    )
    logging.info(summary)
    print(summary)

def main():
    """Handle command-line arguments and run the script."""
    parser = argparse.ArgumentParser(description="PC Cleaner and File Organizer")
    parser.add_argument(
        '--directory',
        type=str,
        help="Directory to organize (e.g., Downloads)"
    )
    parser.add_argument(
        '--delete-duplicates',
        action='store_true',
        help="Delete duplicate files"
    )
    parser.add_argument(
        '--clean-temp',
        action='store_true',
        help="Clean temporary files and cache"
    )
    parser.add_argument(
        '--schedule',
        action='store_true',
        help="Run on a schedule (every 24 hours)"
    )

    args = parser.parse_args()

    if not any([args.directory, args.clean_temp]):
        parser.error("You must specify --directory and/or --clean-temp")

    logging.info("Script started with args: %s", args)

    if args.schedule:
        print("Running in scheduled mode (every 24 hours). Press Ctrl+C to stop.")
        schedule.every(1).days.do(
            run_automation, args.directory, args.delete_duplicates, args.clean_temp
        )
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logging.info("Scheduled run stopped.")
            print("Stopped.")
    else:
        run_automation(args.directory, args.delete_duplicates, args.clean_temp)

if __name__ == "__main__":
    main()
