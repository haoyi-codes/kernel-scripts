#!/usr/bin/env python3

# Script Name: update_kernel_sources.py
# Script Path: <git_root>/scripts/update_kernel_sources.py
# Description: Update kernel sources to /usr/local/src/${hostname}/linux/.

# Copyright (c) 2024 Aryan
# SPDX-License-Identifier: BSD-3-Clause

# Version: 2.1.3

# Import modules to interface with the system.
import argparse
import colorama
import os
import pathlib
import shutil
import socket
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


def colorize(text: str, color:str) -> str:
    """
    Color text based on user defined choice.

    Args:
        text  (str): Text that is about to be printed.
        color (str): Foreground color that the text should be printed in.

    Returns:
        text (str): Text that has been colored or not depending on environment variable.
    """

    # Global variables
    global no_color

    # Color the text if no_color is not set.
    if not no_color:
        text = color + text

    return text


def parse_arguments() -> argparse.Namespace:
    """
    Parse arguments that have been passed in the command line using the argparse
    library.

    Returns:
        args (argparse.Namespace): Command-line arguments parsed using argparse.
    """

    # Parse optional arguments.
    parser = argparse.ArgumentParser(description="Copies latest kernel source and runs make oldconfig.")
    parser.add_argument("--hostname", metavar="HOSTNAME", type=str,
                        default=socket.gethostname(),
                        help="name of the system that needs its source directories updated")
    parser.add_argument("--nocolor", action="store_true",
                        help="disables colored output")
    args = parser.parse_args()

    return args


def main():
    """
    Copies latest kernel source to user's local directory. Then copies the
    previous kernel configuration and runs make oldconfig. Finally, increments
    the MINOR semantic version for the new kernel.
    """

    # Global variables
    global no_color

    # Check if script is run as root.
    check_if_superuser()

    # Parse our command-line arguments.
    args = parse_arguments()
    no_color = args.nocolor
    system_name = args.hostname

    # Obtain environmental variables.
    if os.getenv("NO_COLOR") == "1":
        no_color = True

    # Check if the specified system's root kernel source directory exists.
    local_src_dir = pathlib.Path("/usr/local/src/")
    system_src_dir = local_src_dir / f"{system_name}"
    
    if not system_src_dir.is_dir():
        print(colorize(f"{system_src_dir} does not exist.",
                       colorama.Fore.RED))
        sys.exit(1)

    linux_local_dir = system_src_dir / "linux"

    # Create /usr/local/src/{hostname}/linux/ if not present.
    if not linux_local_dir.is_dir():
        linux_local_dir.mkdir(parents=True)

    # Obtain the path for the latest kernel configuration source.
    src_kernels = []

    for path in pathlib.Path("/usr/src/").iterdir():
        if path.is_dir() and "linux" in path.name and path.name != "linux":
            src_kernels.append(path)

    # Check if there are no kernels available.
    if len(src_kernels) == 0:
        print(colorize(f"Error: There are no kernels available to install" \
                "to the local source directory", colorama.Fore.RED))
        sys.exit(1)

    src_kernels = sorted(src_kernels, reverse=True)
    latest_kernel_path = src_kernels[0]
    latest_local_kernel_path = linux_local_dir / latest_kernel_path.name

    # See if the latest kernel is already present in the user's local src.
    if latest_local_kernel_path.is_dir():
        print(colorize(f"The latest kernel version {latest_kernel_path.name} already exists in {linux_local_dir}.",
                       colorama.Fore.RED))
        sys.exit(1)

    # Copy the latest kernel source to user's local linux directory.
    print(colorize(f"Copying {latest_kernel_path.name} to {linux_local_dir}...",
                   colorama.Style.RESET_ALL))
    try:
        shutil.copytree(latest_kernel_path, latest_local_kernel_path)
        print(colorize(f"Sucessfully copied {latest_kernel_path.name} to {linux_local_dir}.",
                       colorama.Fore.GREEN))
    except Exception as e:
        print(colorize(f"Error copying {latest_kernel_path.name} to {linux_local_dir}.",
                       colorama.Fore.RED))
        sys.exit(1)

    # Obtain the previous kernel config and copy it to the new linux source.
    local_kernels = []

    for path in linux_local_dir.iterdir():
        if path.is_dir() and "linux" in path.name:
            local_kernels.append(path)

    local_kernels = sorted(local_kernels, reverse=True)
    
    # Since we added our newer kernel source it will be the second entry in the list.
    prev_local_kernel_path = local_kernels[1]
    prev_kernel_config = prev_local_kernel_path / ".config"
    latest_kernel_config = latest_local_kernel_path / ".config"

    try:
        shutil.copyfile(prev_kernel_config, latest_kernel_config)
        print(colorize(f"Copied {prev_local_kernel_path.name}'s config to {latest_local_kernel_path.name}.",
                       colorama.Fore.GREEN))
    except Exception as e:
        print(colorize(f"Error copying {prev_local_kernel_path.name}'s config to {latest_local_kernel_path}.",
                       colorama.Fore.RED))
        sys.exit(1)

    # Ask the user if they want to make oldconfig.
    while True:
        user_input = input(colorize("Would you like to make oldconfig? (Y/n) ",
                                    colorama.Style.RESET_ALL)).strip().lower()
        print("")

        if user_input == "" or user_input == "y" or user_input == "yes":
            break
        elif user_input == "n" or user_input == "no":
            print(colorize(f"Exiting...", colorama.Fore.GREEN))
            sys.exit(0)
        else:
            print(colorize(f"\nInvalid input: \"{user_input}\"",
                           colorama.Fore.RED))
            print(colorize(f"Please try again.", colorama.Fore.RED))

    # Change directory to the new kernel source in the users local directory.
    os.chdir(latest_local_kernel_path)

    # Make oldconfig
    try:
        print(colorize(f"Making oldconfig...", colorama.Style.RESET_ALL))
        result = subprocess.run(['make', 'oldconfig'], check=True)
    except Exception as e:
        print(colorize(f"Error making oldconfig: {e}", colorama.Fore.RED))
        sys.exit(1)

    # Increment the semver MINOR version in the latest kernel config.

    ## Create a string of all the lines of the old config.
    config_lines = latest_kernel_config.read_text().splitlines()

    ## Create a new list based on that to manipulate.
    new_config_lines = config_lines.copy()

    ## Enumerate helps us to identify the position of an item in a list.
    for n, line in enumerate(new_config_lines):
        # Obtain the local version line.
        if line.startswith("CONFIG_LOCALVERSION="):

            # Split line up into [ 'CONFIG_LOCALVERSION', '-{hostname}-X.Y.Z' ].
            # And remove quotation mark.
            parts = line.replace('"', "").split("=")

            # Split up the "version" part into [ '"', '{hostname}', 'X.Y.Z' ].
            version_parts = parts[1].split("-")

            # Split up semantic version into [ 'X', 'Y', 'Z' ].
            sem_version = version_parts[2].split(".")

            # Obtain the MINOR version.
            minor_version = int(sem_version[1])

            # Increment the MINOR version.
            new_minor_version = str(minor_version + 1)

            # Recreate the line with the new MINOR version. 
            new_sem_version = f"{sem_version[0]}.{new_minor_version}.{sem_version[2]}"
            version_parts[2] = new_sem_version

            # Since version_parts is a list we want to insert it into parts
            # without parts becoming a list of lists.
            parts[1:] = version_parts
            parts = [ parts[0], '=', '"', '-', parts[2], '-', parts[3], '"' ]
            new_line = "".join(parts)

            # Replace the local version line with our new_line
            new_config_lines[n] = new_line

    # Make the list into a string to write back to the config file.
    new_config = "\n".join(new_config_lines)

    # Write the new_config to .config.
    try:
        latest_kernel_config.write_text(new_config)
        print(colorize(f"Incremented kernel SEMVER to {new_sem_version}.",
                       colorama.Fore.GREEN))
    except IOError as e:
         print(colorize(f"An error occurred while writing to {latest_local_kernel_path.name}'s config file: {e}",
                        colorama.Fore.RED))
         sys.exit(1)

    # Success!
    print(colorize(f"Updated kernel source to {latest_kernel_path.name}-{system_name}-{new_sem_version}. Exiting...", colorama.Fore.GREEN))


if __name__ == "__main__":
    main()
