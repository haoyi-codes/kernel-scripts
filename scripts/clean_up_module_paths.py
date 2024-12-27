#!/usr/bin/env python3

# Script Name: clean_up_module_paths.py
# Script Path: <git_root>/scripts/clean_up_module_paths.py
# Description: Prune deprecated module directories.

# Copyright (c) 2024 Aryan
# SPDX-License-Identifier: BSD-3-Clause

# Version: 1.6.3

# Import modules to interface with the system.
import colorama
import os
import pathlib
import shutil
import sys

def check_if_superuser():
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


def colorize(text, color):
    """
    Check if NO_COLOR environment variable is set or if the global parameter
    no_color exists. Then color text accordingly.

    Args:
        text (str): Text that is about to be printed.
        color (str): Foreground color that the text should be printed in.

    Returns:
        text (str): Text that has been colored or not depending on environment
                    variable.
    """
    global no_color
    
    if "no_color" not in globals():
        no_color = os.getenv("NO_COLOR")

    if no_color != "1":
        text = color + text

    return text


def list_contents(parent_dir):
    """
    List out the contents of parent_dir and store their absolute paths in a
    list called contents. Then return that list sorted in descending order.

    Args:
        parent_dir (pathlib.PosixPath): The absolute path to where the parent directory is.

    Returns:
        sorted_contents (list): A sorted list of all the absolute paths of
                                parent_dir's contents in descending order.
    """

    contents = []

    # Append the absolute paths for every sub directory in the parent
    # directory to the contents list.
    for sub_dir in parent_dir.iterdir():
        sub_dir_absolute_path = sub_dir.resolve()
        contents.append(sub_dir_absolute_path)

    # If there are only 2 or less directories in the parent directory it has
    # already been pruned so we can exit successfully.
    if len(contents) <= 2:
        print(colorize(f"/lib/modules has already been pruned.",
              colorama.Fore.GREEN))
        sys.exit(0) # Exit successfully

    # Sort the list from highest to lowest to get the newest directories at the
    # start.
    sorted_contents = sorted(contents, reverse=True)
    return sorted_contents


def main():
    # Check if script is run as root.
    check_if_superuser()

    # Sort module directories based on version in descending order.
    parent_dir = "/lib/modules/"
    parent_dir = pathlib.Path(parent_dir)
    sorted_contents = list_contents(parent_dir)

    # Ask if the user wants to remove deprecated directories.
    paths_to_remove = removal_prompt(sorted_contents)

    # Remove the deprecated directories.
    remove_modules(paths_to_remove)

    # Success!
    print(colorize(f"\nSuccessfully pruned /lib/modules. Exiting...",
                   colorama.Fore.GREEN))


def removal_prompt(sorted_contents):
    """
    Prompt the user if they want to remove the older directories; otherwise,
    exit.

    Args:
        sorted_contents (list): A sorted list in descending order of the absolute paths
                         to the target directories.

    Returns:
        paths_to_remove (list): A list of absolute paths to the directories that
                                are planned to be removed.
    """

    # Inform the user that all the directories apart from the latest two are to be removed.

    print("\nWe will keep the latest two module paths:\n")
    saved_paths = sorted_contents[:2]

    for item in saved_paths:
        print(item)

    print("\nWe will remove the following module paths:\n")
    paths_to_remove = sorted_contents[2:]

    for item in paths_to_remove:
        print(item)

    # Ask the user if they want to continue with the removal process.
    while True:
        user_input = input("\nWould you like to remove these paths? (Y/n) ").strip().lower()

        if user_input == "" or user_input == "y" or user_input == "yes":
            break
        elif user_input == "n" or user_input == "no":
            print(colorize(f"\nExiting...", colorama.Fore.GREEN))
            sys.exit(0) # Exit successfully
        else:
            print(colorize(f"\nInvalid input: \"{user_input}\".",
                           colorama.Fore.RED))
            print(colorize(f"Please try again.", colorama.Fore.RED))

    return paths_to_remove


def remove_modules(paths_to_remove):
    """
    Remove all directories in the paths_to_remove list.

    Args:
        paths_to_remove (list): A list of absolute paths to the directories that
                                are planned to be removed.

    Returns:
        None: This function does not return a value.

    Raises:
        Exception: If there was an issue with removing a directory.
    """

    print("")

    # Try removing each directory and if it doesn't work throw an error.
    for path in paths_to_remove:
        try:
            if path.is_dir():
                shutil.rmtree(path)
                print(colorize(f"Removed {path}.", colorama.Fore.GREEN))
        except Exception as e:
            print(colorize(f"Error removing {path}: {e}", colorama.Fore.RED))

    return None


if __name__ == "__main__":
    main()
