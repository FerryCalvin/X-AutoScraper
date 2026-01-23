
import os

file_path = r"d:\project101\autoscraper\logs\autoscraper.log"

try:
    import time
    mtime = os.path.getmtime(file_path)
    size = os.path.getsize(file_path)
    print(f"Log Size: {size} bytes")
    print(f"Last Modified: {time.ctime(mtime)}")
    
    # Read last 5 lines just to be sure
    with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        for line in lines[-5:]:
            print(line.strip())
except Exception as e:
    print(f"Error: {e}")
