
import os

file_path = r"d:\project101\autoscraper\logs\autoscraper.log"
try:
    with open(file_path, "rb") as f:
        # Move to end of file
        f.seek(0, 2)
        file_size = f.tell()
        
        # Read last 20000 bytes
        to_read = min(20000, file_size)
        f.seek(-to_read, 2)
        
        lines = f.readlines()
        
        # Decode and print last 200 lines
        print("\n".join([line.decode('utf-8', errors='ignore').strip() for line in lines[-200:]]))
except Exception as e:
    print(f"Error reading log: {e}")
