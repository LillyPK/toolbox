import os
import sys
import json
import subprocess
import platform
import urllib.request
import hashlib
from pathlib import Path
import shutil
import zipfile
from datetime import datetime
import warnings
import platform
from tqdm import tqdm
from tqdm.std import TqdmWarning
from colorama import Fore, Style
import argparse

warnings.filterwarnings("ignore", category=TqdmWarning)

def get_package_file_path():
    if platform.system() == "Windows":
        return Path(os.getenv('APPDATA')) / "ravendevteam" / "toolbox" / "packages.json"
    else:
        return Path.home() / "Library" / "Application Support" / "ravendevteam" / "toolbox" / "packages.json"

def get_installation_path(package_name):
    if platform.system() == "Windows":
        return Path(os.getenv('APPDATA')) / "ravendevteam" / package_name
    else:
        return Path.home() / "Library" / "Application Support" / "ravendevteam" / package_name

def handle_error(message):
    print(Fore.RED + f"Error: {message}" + Style.RESET_ALL)
    sys.exit(1)

def handle_warning(message):
    print(Fore.YELLOW + f"Warning: {message}" + Style.RESET_ALL)

def get_record_file_path():
    if platform.system() == "Windows":
        return Path(os.getenv('APPDATA')) / "ravendevteam" / "record.json"
    else:
        return Path.home() / "Library" / "Application Support" / "ravendevteam" / "record.json"

def read_record():
    record_file = get_record_file_path()
    if not record_file.exists():
        return {}
    try:
        with open(record_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_record(record):
    record_file = get_record_file_path()
    record_file.parent.mkdir(parents=True, exist_ok=True)
    with open(record_file, 'w') as f:
        json.dump(record, f, indent=4)

def uninstall_package(package_name, skip_confirmation):
    try:
        install_path = get_installation_path(package_name)
        if not install_path.exists():
            handle_error(f"Package '{package_name}' is not installed.")
        if not skip_confirmation:
            confirmation = input(f"Are you sure you want to uninstall '{package_name}'? (Y/N): ").strip().lower()
            if confirmation != 'y':
                print(Fore.WHITE + f"Uninstallation of '{package_name}' cancelled." + Style.RESET_ALL)
                return
        shutil.rmtree(install_path)
        print(Fore.GREEN + f"'{package_name}' has been successfully uninstalled." + Style.RESET_ALL)
        record = read_record()
        if package_name in record:
            del record[package_name]
            write_record(record)
    except Exception as e:
        handle_error(f"An error occurred while uninstalling '{package_name}': {str(e)}. Please try again.")

def ensure_packages_file():
    package_file_path = get_package_file_path()
    if not package_file_path.exists():
        print(Fore.YELLOW + f"Package list not found at {package_file_path}. Downloading..." + Style.RESET_ALL)
        url = "https://raw.githubusercontent.com/ravendevteam/toolbox/main/packages.json"
        try:
            package_file_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, package_file_path)
            print(Fore.GREEN + f"Package list downloaded successfully to {package_file_path}." + Style.RESET_ALL)
        except Exception as e:
            handle_error(f"Failed to download package list: {e}")

def update_packages():
    default_update_url = "https://raw.githubusercontent.com/ravendevteam/toolbox/main/packages.json"
    try:
        with open(get_package_file_path(), 'r') as f:
            data = json.load(f)
        update_url = data.get('updateurl', default_update_url)
    except (FileNotFoundError, json.JSONDecodeError):
        update_url = default_update_url
        print(Fore.YELLOW + f"Package list is missing or invalid. Using default update URL: {default_update_url}" + Style.RESET_ALL)
    print(Fore.WHITE + f"Updating package list from: {update_url}" + Style.RESET_ALL)
    try:
        urllib.request.urlretrieve(update_url, get_package_file_path())
        print(Fore.GREEN + "Package list updated successfully!" + Style.RESET_ALL)
    except Exception as e:
        handle_error(f"Failed to update package list: {e}")

def list_packages():
    try:
        ensure_packages_file()
        with open(get_package_file_path(), 'r') as f:
            data = json.load(f)
        print(Fore.WHITE + "Available Packages:\n" + Style.RESET_ALL)
        for package in data.get("packages", []):
            print(Fore.CYAN + f"Name: {package['name']}" + Style.RESET_ALL)
            print(f"Version: {package['version']}")
            print(f"Description: {package['description']}")
            print(f"Available for: {', '.join(package['os'])}")
            print(f"Requires Path: {'Yes' if package['requirepath'] else 'No'}")
            print(f"Creates Shortcut: {'Yes' if package['shortcut'] else 'No'}")
            print(Fore.MAGENTA + "-" * 40 + Style.RESET_ALL)
    except FileNotFoundError:
        handle_error("Package list not found. Try running the 'update' command to fetch the package list.")
    except json.JSONDecodeError:
        handle_error("Failed to read package list (corrupted or invalid JSON).")

def validate_checksum(file_path, expected_hash):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_hash

def create_shortcut(target, shortcut_name):
    """
    Creates a .lnk shortcut on Windows using PowerShell.

    Args:
        target (str): The path to the target file (e.g., an executable).
        shortcut_name (str): The name of the shortcut.
    """
    try:
        if platform.system() == "Windows":
            # Windows: Create a .lnk shortcut using PowerShell
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")

            # Ensure the desktop directory exists
            if not os.path.exists(desktop):
                os.makedirs(desktop)

            # PowerShell script to create a .lnk file
            ps_script = f"""
            $WshShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{target}"
            $Shortcut.WorkingDirectory = "{os.path.dirname(target)}"
            $Shortcut.IconLocation = "{target},0"
            $Shortcut.Save()
            """

            # Run the PowerShell script
            subprocess.run(["powershell", "-Command", ps_script], check=True)
            print(Fore.GREEN + f"Shortcut created at {shortcut_path}" + Style.RESET_ALL)

        else:
            # macOS/Linux: Create a symbolic link on the desktop
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, shortcut_name)

            # Ensure the desktop directory exists
            if not os.path.exists(desktop):
                os.makedirs(desktop)

            # Create the symbolic link
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)  # Remove existing link if it exists
            os.symlink(target, shortcut_path)
            print(Fore.GREEN + f"Symbolic link created at {shortcut_path}" + Style.RESET_ALL)

    except Exception as e:
        handle_warning(f"Could not create a shortcut for '{shortcut_name}': {e}")

def install_package(package_name, skip_confirmation):
    try:
        ensure_packages_file()
        with open(get_package_file_path(), 'r') as f:
            data = json.load(f)
        packages = data.get("packages", [])
        if package_name == '*':
            for package in packages:
                install_package(package['name'], skip_confirmation)
            return
        package = next((pkg for pkg in packages if pkg["name"].lower() == package_name.lower()), None)
        if not package:
            handle_error(f"Package '{package_name}' not found in the package list.")
        platform_name = platform.system()
        if platform_name not in package["os"]:
            handle_error(f"'{package_name}' is not available for your platform ({platform_name}).")
        if not skip_confirmation:
            confirmation = input(f"Are you sure you want to install '{package_name}'? (Y/N): ").strip().lower()
            if confirmation != 'y':
                print(Fore.WHITE + f"Installation of '{package_name}' cancelled." + Style.RESET_ALL)
                return
        url = package["url"][platform_name]
        sha256 = package["sha256"][platform_name]
        print(Fore.WHITE + f"Installing {package_name} (v{package['version']}) for {platform_name}..." + Style.RESET_ALL)
        install_path = get_installation_path(package_name)
        install_path.mkdir(parents=True, exist_ok=True)
        download_path = install_path / f"{package_name}.{url.split('.')[-1]}"
        with tqdm(total=100, desc="Downloading", unit='%', bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
            urllib.request.urlretrieve(
                url, download_path, 
                reporthook=lambda count, block_size, total_size: pbar.update(block_size / total_size * 100)
            )
        print(Fore.WHITE + f"Downloaded {package_name} to {download_path}" + Style.RESET_ALL)
        if not validate_checksum(download_path, sha256):
            handle_error(f"Checksum mismatch for {package_name}. Installation aborted.")
        if install_path.exists():
            print(Fore.GREEN + f"{package_name} installed successfully!" + Style.RESET_ALL)
            if package['shortcut']:
                target = next(install_path.glob('*'), None)
                if target:
                    create_shortcut(str(target), package_name)
            record = read_record()
            record[package_name] = {
                "version": package["version"],
                "installed_on": datetime.now().isoformat()
            }
            write_record(record)
    except FileNotFoundError:
        handle_error("Package list not found. Try updating the package list using the 'update' command.")
    except Exception as e:
        handle_error(f"An error occurred during installation: {e}.")

def main():
    print(Fore.CYAN + "Welcome to the Toolbox Package Manager!" + Style.RESET_ALL)
    print("Type 'help' for a list of commands or 'exit' to quit.")

    while True:
        try:
            user_input = input(Fore.WHITE + "toolbox> " + Style.RESET_ALL).strip()
            if not user_input:
                continue

            if user_input.lower() == "exit":
                print(Fore.GREEN + "Goodbye!" + Style.RESET_ALL)
                break

            args = user_input.split()
            command = args[0].lower()
            package = args[1] if len(args) > 1 else None
            skip_confirmation = "-y" in args or "--yes" in args

            if command == "list":
                list_packages()
            elif command == "install":
                if not package:
                    handle_error("You must specify the package name to install.")
                install_package(package, skip_confirmation)
            elif command == "uninstall":
                if not package:
                    handle_error("You must specify the package name to uninstall.")
                uninstall_package(package, skip_confirmation)
            elif command == "update":
                update_packages()
            elif command == "help":
                print("""
Available Commands:
list               List all available packages.
install <package>  Install the specified package.
uninstall <package> Uninstall the specified package.
update             Update the package list.
exit               Exit the application.
                """)
            else:
                handle_warning("Unknown command. Type 'help' for a list of commands.")
        except KeyboardInterrupt:
            print(Fore.GREEN + "\nGoodbye!" + Style.RESET_ALL)
            break
        except Exception as e:
            handle_error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
