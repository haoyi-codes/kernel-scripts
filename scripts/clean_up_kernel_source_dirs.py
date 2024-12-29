#!/usr/bin/env python3

# Script Name: clean_up_module_kernel_source_dirs.py
# Script Path: <git_root>/scripts/clean_up_kernel_source_dirs.py
# Description: Prune deprecated directories in
# /usr/local/src/${system}/{linux,uki,vmlinuz}.

# Copyright (c) 2024 Aryan
# SPDX-License-Identifier: BSD-3-Clause

# Version: 2.0.1

# Import modules to interface with the system.
import argparse
import colorama
import os
import pathlib
import shutil
import socket
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


def create_prunable_list(src_dir) -> typing.Optional[list]:
    """
    Create a list of contents of all available files and subdirectories in the
    kernel source directory that are prunable.

    Args:
        src_dir (pathlib.PosixPath): The absolute path of the kernel source
                                     directories.

    Returns:
        available_dirs (Optional[list]): List of all the available files/directories that
                                         can be pruned, otherwise returns None.
    """

    # Define prunable directories.
    prunable_dirs = [ "linux", "uki", "vmlinuz" ]
    available_dirs = []

    for sub_dir in src_dir.iterdir():
        temp_list = []
        
        # Check if any of the subdirectories match our prunable directories if
        # so add them to our list.
        if sub_dir.name in prunable_dirs:
            for sub_sub_dir in sub_dir.resolve().iterdir():
                temp_list.append(sub_sub_dir)

            # Sort the temp_list from newest to oldest version.
            sorted_temp_list = sorted(temp_list, reverse=True)

            # Append the sorted list to our list of lists.
            available_dirs.append(sorted_temp_list)
    
    # If our list of lists is empty return None
    if len(available_dirs) == 0:
        return None
    else:
        return available_dirs


def parse_arguments() -> str:
    """
    Parse arguments that have been passed in the command line using the argparse
    library.

    Returns:
        system_name (str): The name of the system that needs its kernel source
                           directories pruned.
    """

    # Specify the global no_color variable.
    global no_color

    # Parse optional arguments.
    parser = argparse.ArgumentParser(description="Prune deprecated kernel source files/directories.")
    parser.add_argument("--nocolor", action="store_true",
                        help="disables colored output.")
    parser.add_argument("system_name", nargs="?", type=str,
                        help="name of system that needs its source directories pruned.")
    args = parser.parse_args()

    # Set the global variable no_color to 1 if user passed --nocolor.
    if args.nocolor:
       no_color = "1" 

    # If the user doesn't pass a system_name assume its the hostname.
    if args.system_name is None:
        system_name = socket.gethostname()
    else:
        system_name = args.system_name

    return system_name

def removal_prompt(sub_list) -> typing.Optional[list]:
    """
    Prompt the user if they want to remove deprecated files/directories.

    Args:
        sub_list (list): A sorted list in descending order of the absolute paths
                         to the target files/directories within a specific
                         subdirectory (i.e linux, uki, vmlinuz).

    Returns:
        paths_to_remove (Optional[list]): A list of absolute paths to the files/directories that
                                          are planned to be removed, otherwise
                                          returns None.
    """

    path_name = pathlib.Path(sub_list[0]).parts[5]

    # If there are only 2 or less files/directories in the parent directory it has
    # already been pruned.
    if len(sub_list) <= 2:
        print(colorize(f"The {path_name} directory has already been pruned.\n", colorama.Fore.GREEN))
        return None

    # Inform the user that all the files/directories apart from the latest two are to be removed.
    print(colorize(f"We will keep the latest two {path_name} files/directories:\n",
                   colorama.Style.RESET_ALL))
    saved_paths = sub_list[:2]

    for item in saved_paths:
        print(item)

    print("")
    print(colorize(f"We will remove the following {path_name} files/directories:\n",
                   colorama.Style.RESET_ALL))
    paths_to_remove = sub_list[2:]

    for item in paths_to_remove:
        print(item)

    print("")

    # Ask the user if they want to continue with the removal process.
    while True:
        user_input = input(colorize("Would you like to remove these paths? (Y/n) ",
                                    colorama.Style.RESET_ALL)).strip().lower()
        print("")

        if user_input == "" or user_input == "y" or user_input == "yes":
            return paths_to_remove
        elif user_input == "n" or user_input == "no":
            return None
        else:
            print(colorize(f"\nInvalid input: \"{user_input}\"",
                           colorama.Fore.RED))
            print(colorize(f"Please try again.", colorama.Fore.RED))


def prune_list(removal_list) -> None:
    """
    Remove all directories in the removal_list list.

    Args:
        removal_list (list): A list of lists of absolute paths to the files/directories that
                             are planned to be removed.

    Returns:
        None: This function does not return a value.

    Raises:
        Exception: If there was an issue with removing a file/directory.
    """

    # Remove each element in the list of lists.
    for sub_list in removal_list:
        for path in sub_list:
            # Try removing each file/directory and if it doesn't work throw an error.
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    print(colorize(f"Removed {path}.\n", colorama.Fore.GREEN))
                elif path.is_file():
                    path.unlink()
                    print(colorize(f"Removed {path}.\n", colorama.Fore.GREEN))
            except Exception as e:
                print(colorize(f"Error removing {path}: {e}", colorama.Fore.RED))
                sys.exit(1)

    return None


def main():
    """
    Create a list of lists of deprecated kernel source files/directories and
    prompt user for removal. If permission is granted remove them.
    """

    # Check if script is run as root.
    check_if_superuser()

    # Parse our command line arguments and obtain the system name.
    system_name = parse_arguments()

    # Check if the specified system's root kernel source directory exists.
    local_src_dir = pathlib.Path("/usr/local/src/")
    system_src_dir = local_src_dir / f"{system_name}"
    
    if not system_src_dir.is_dir():
        print(colorize(f"{system_src_dir} does not exist.",
                       colorama.Fore.RED))
        sys.exit(1)

    # Obtain a sorted list of lists of all prunable files/directories.
    sorted_contents = create_prunable_list(system_src_dir)

    # If no directories are found for pruning then user does not have their
    # kernel source directories in the right format.
    if sorted_contents is None:
        print(colorize(f"No available directories have been found that can be \
                         pruned. Please make sure you have your directories in the \
                         correct format.", colorama.Fore.RED))
        sys.exit(1)

    # Ask if the user wants to remove deprecated files/directories and add them to a
    # list.
    removal_list = []

    ## If the user has chosen not to remove certain files/directories don't add
    ## them to the removal list.
    for sub_list in sorted_contents:
        temp_removal_list = removal_prompt(sub_list)

        if temp_removal_list is not None:
            removal_list.append(temp_removal_list)

    # If the removal_list is empty then we can just exit as everything has been
    # pruned already.
    if len(removal_list) == 0:
        print(colorize("Exiting...\n", colorama.Fore.GREEN))
        sys.exit(0)

    # Remove the deprecated files/directories.
    prune_list(removal_list)

    # Success!
    print(colorize(f"Successfully pruned all chosen kernel source directories! Exiting...\n", colorama.Fore.GREEN))


if __name__ == "__main__":
    main()
