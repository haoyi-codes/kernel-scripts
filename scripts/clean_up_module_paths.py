#!/usr/bin/env python3

# Script Name: clean_up_module_paths.py
# Script Path: <git_root>/scripts/clean_up_module_paths.py
# Description: Prune deprecated module directories.

# Copyright (c) 2024 Aryan
# SPDX-License-Identifier: BSD-3-Clause

# Version: 1.0.1

# Import modules to interface with the system.
import os
import shutil
import sys

# Colors
green="\033[0;32m"
red="\033[0;31m"
nc="\033[0m"

def check_if_superuser():
    if os.getuid() != 0:
        print(f"{red}{os.path.basename(sys.argv[0])}: must be superuser.{nc}")
        sys.exit(1)

    return None


def list_contents(parent_dir):
    contents_path = []

    for sub_dir in os.listdir(parent_dir):
        absolute_sub_dir_path = os.path.join(parent_dir, sub_dir)
        contents_path.append(absolute_sub_dir_path)

    if len(contents_path) <= 2:
        print(f"{green}The module paths have already been pruned.{nc}")
        sys.exit(0)

    sorted_contents_path = sorted(contents_path, reverse=True)
    print("Here is a list of all the available module directories in /lib/modules/:\n")

    for item in sorted_contents_path:
        print(item)

    return sorted_contents_path


def removal_prompt(contents):
    print("\nWe will keep the latest two module paths, which are:\n")
    saved_paths = contents[:2]

    for item in saved_paths:
        print(item)

    print("\nWe will remove the following module paths:\n")
    paths_to_remove = contents[2:]

    for item in paths_to_remove:
        print(item)

    while True:
        user_input = input("\nWould you like to remove these paths? (Y/n) ").strip().lower()

        if user_input == "" or user_input == "y" or user_input == "yes":
            break
        elif user_input == "n" or user_input == "no":
            print(f"\n{green}Exiting...{nc}")
            sys.exit(0)
        else:
            print(f"\n{red}Invalid input: \"{user_input}\".{nc}")
            print(f"{red}Please try again.{nc}")

    return paths_to_remove


def remove_modules(paths_to_remove):
    print("\n")

    for path in paths_to_remove:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"{green}Removed {path}.{nc}")
        except Exception as e:
            print(f"{red}Error removing {path}: {e}{nc}")

    return None


def main():
    check_if_superuser()
    contents = list_contents("/lib/modules/")
    paths_to_remove = removal_prompt(contents)
    remove_modules(paths_to_remove)
    print(f"\n{green}Sucessfully removed all module paths. Exiting...{nc}")


if __name__ == "__main__":
    main()
