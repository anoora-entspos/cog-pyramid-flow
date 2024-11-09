import os
import subprocess
import time

# Constants
BASE_URL = "https://weights.replicate.delivery/default/pyramid-flow/"
MODEL_PATH = "pyramid-flow-model"
MODEL_FILE = "pyramid-flow-model.tar"

url = BASE_URL + MODEL_FILE
filename = url.split("/")[-1]
dest_path = os.path.join(MODEL_PATH, filename)

def download_weights(url: str, dest: str) -> None:
    # Ensure the destination directory exists
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    
    start = time.time()
    print("[!] Initiating download from URL: ", url)
    print("[~] Destination path: ", dest)
    
    # Run the wget command to download the file
    command = ["wget", "-O", MODEL_FILE, url]
    try:
        print(f"[~] Running command: {' '.join(command)}")
        subprocess.check_call(command, close_fds=False)
    except subprocess.CalledProcessError as e:
        print(
            f"[ERROR] Failed to download weights. Command '{' '.join(e.cmd)}' returned non-zero exit status {e.returncode}."
        )
        raise
    print("[+] Download completed in: ", time.time() - start, "seconds")
    
    # If the downloaded file is a .tar file, extract it
    if dest.endswith(".tar"):
        print("[~] Extracting the tar file...")
        try:
            # Run the tar command to extract the file
            extract_command = ["tar", "-xvf", dest, "-C", MODEL_PATH]
            print(f"[~] Running extraction command: {' '.join(extract_command)}")
            subprocess.check_call(extract_command, close_fds=False)
            print("[+] Extraction completed successfully.")
        except subprocess.CalledProcessError as e:
            print(
                f"[ERROR] Failed to extract the tar file. Command '{' '.join(e.cmd)}' returned non-zero exit status {e.returncode}."
            )
            raise

# Call the download function
download_weights(url, dest_path)
