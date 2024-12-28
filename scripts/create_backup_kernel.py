#!/usr/bin/env python3

# Script Name: create_backup_kernel.py
# Script Path: <git_root>/scripts/create_backup_kernel.py
# Description: Copy the current bootx64.efi to the backup location specified by efibootmgr.

# Copyright (c) 2024 Aryan
# SPDX-License-Identifier: BSD-3-Clause

# Version: 2.0.0

# Import standard libraries.
import argparse
import colorama
import os
import pathlib
import shutil
import subprocess
import sys
import typing


def check_if_superuser() -> None:
    """
    Check if the user is root. If the user isn't root then it exits the script
    with a failure.

    Returns:
        None: This function does not return a value.
    """

    # Check if uid = 0 (root) to continue.
    if os.getuid() != 0:
        program_name = pathlib.Path(sys.argv[0]).name
        print(colorize(f"{program_name}: must be superuser.", colorama.Fore.RED))
        sys.exit(1) # Exit with error code 1

    return None


def colorize(text, color) -> str:
    """
    Check if NO_COLOR environment variable is set or if the global parameter
    no_color exists. Then color text accordingly.

    Args:
        text  (str): Text that is about to be printed.
        color (str): Foreground color that the text should be printed in.

    Returns:
        text (str): Text that has been colored or not depending on environment
                    variable.
    """

    # Specify the global no_color variable.
    global no_color
    
    # If the global no_color variable is not set take the value from the
    # ENVIRONMENT.
    if "no_color" not in globals():
        no_color = os.getenv("NO_COLOR")

    # Color the text if no_color is not set.
    if no_color != "1":
        text = color + text

    return text


def get_kernel_version(efi_file_path) -> typing.Optional[str]:
    """
    Obtain the kernel version using file and capturing the 9th substring.

    Args:
        efi_file_path (pathlib.PosixPath): The path to the main kernel efi file.

    Returns:
        kernel_version (Optional[str]): Returns the kernel version, otherwise
                                        returns None.
    """

    try:
        # Use the file command to obtain infromation
        result = subprocess.run(["file", efi_file_path], capture_output=True,
                                text=True, check=True)

        # Create a list based on splitting up the stdout into smaller substrings.
        output_list = result.stdout.split()

        # Obtain the 9th value (similar to 'awk[-ing]' the 9th substring).
        if len(output_list) >= 9:
            kernel_version = output_list[8]
            return kernel_version
        else:
            return None
    except subprocess.CalledProcessError as e:
        print(colorize(f"Error executing file {efi_file_path}: {e}",
                       colorama.Fore.RED))
    except Exception as e:
        print(colorize(f"Unknown error when obtaining version for {efi_file_path}: {e}",
                       colorama.Fore.RED))


def mount_dir(mount_path) -> None:
    """
    Mount the directory specified by mount_path.

    Args:
        mount_path (pathlib.PosixPath): The path to the directory that should be
                                        mounted.

    Returns:
        None: This function does not return a value.
    """

    # Use the mount command.
    try:
        subprocess.run(["mount", mount_path], check=True)
    except subprocess.CalledProcessError as e:
        print(colorize(f"Failed to mount {mount_path}: {e}",
                       colorama.Fore.RED))
    except Exception as e:
        print(colorize(f"Unknown error when mounting {mount_path}: {e}",
                       colorama.Fore.RED))


def unmount_dir(mount_path) -> None:
    """
    Unmount the directory specified by mount_path.

    Args:
        mount_path (pathlib.PosixPath): The path to the directory that should be
                                        unmounted.

    Returns:
        None: This function does not return a value.
    """

    # Use the unmount command.
    try:
        subprocess.run(["umount", mount_path], check=True)
    except subprocess.CalledProcessError as e:
        print(colorize(f"Failed to unmount {mount_path}: {e}",
                       colorama.Fore.RED))
    except Exception as e:
        print(colorize(f"Unknown error when unmounting {mount_path}: {e}",
                       colorama.Fore.RED))


def parse_arguments() -> None:
    """
    Parse arguments that have been passed in the command line using the argparse
    library.

    Returns:
        None: This function does not return a value.
    """

    # Specify the global no_color variable.
    global no_color

    # Parse optional arguments.
    parser = argparse.ArgumentParser(description="Copies the main boot kernel efi file to the backup location.")
    parser.add_argument("--nocolor", action="store_true",
                        help="disables colored output.")
    args = parser.parse_args()

    # Set the global variable no_color to 1 if user passed --nocolor.
    if args.nocolor:
       no_color = "1" 

    return None


def main():
    """
    Mount the boot directory then copy the main kernel/uki efi file to the
    backup location. After that is done unmount the boot directory.
    """
    
    # Check if script is run as root.
    check_if_superuser()

    # Pass the command line arguments.
    parse_arguments()

    # Mount the boot directory.
    boot_dir = pathlib.Path("/boot/")

    # Check if the directory exists.
    if not boot_dir.is_dir():
        print(colorize(f"The directory {boot_dir} does not exist.",
                       colorama.Fore.RED))
        sys.exit(1)

    mount_dir(boot_dir)

    # Copy bootx64.efi to backup.efi.
    main_boot_efi_path = pathlib.Path("/boot/efi/boot/bootx64.efi")
    backup_boot_efi_path = pathlib.Path("/boot/efi/boot/backup.efi")

    # Obtain kernel version for the kernel we are copying.
    kernel_version = get_kernel_version(main_boot_efi_path)

    if kernel_version is None:
        print(colorize(f"Error obtaining the kernel version for {main_boot_efi_path}",
                       colorama.Fore.RED))
        unmount_dir(boot_dir)
        sys.exit(1)

    try:
        shutil.copy(main_boot_efi_path, backup_boot_efi_path)
        print(colorize(f"Successfully copied {kernel_version} to {backup_boot_efi_path}.",
                       colorama.Fore.GREEN))
    except Exception as e:
        print(colorize(f"Failed to copy {kernel_version} to backup location: {e}",
                       colorama.Fore.RED))
        unmount_dir(boot_dir)
        sys.exit(1)

    # Unmount the boot directory.
    unmount_dir(boot_dir)


if __name__ == "__main__":
    main()
