import subprocess
import sys

def install_requirements():
    requirements = [
        'selenium',
        'undetected-chromedriver',
        'websocket-client',
        'requests',
        'python-dotenv'
    ]
    
    print("Installing required packages...")
    
    for package in requirements:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}: {e}")
            return False
    
    print("\nAll requirements installed successfully!")
    return True

if __name__ == "__main__":
    install_requirements()