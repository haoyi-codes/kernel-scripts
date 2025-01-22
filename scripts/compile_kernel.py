#!/usr/bin/env python3

# Script Name: compile_kernel.py
# Script Path: <git_root>/scripts/compile_kernel.py
# Description: Automated kernel compilation script.

# Copyright (c) 2024 Aryan
# SPDX-License-Identifier: BSD-3-Clause

# Version: 1.0.5

# Import modules to interface with the system.
import argparse
import colorama
import os
import pathlib
import shutil
import socket
import subprocess
import sys


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


def check_for_executable(ex_name: str) -> bool:
    """
    Checks if executable is installed in the user's PATH.

    Args:
        ex_name (str): The name of the executable.

    Returns:
        found (bool): If True that means the executable is in the user's PATH.
        
    """

    path_dirs = os.environ.get("PATH").split(os.pathsep)
    found = False

    for directory in path_dirs:
        ex_path = pathlib.Path(directory) / f"{ex_name}"

        if ex_path.exists():
            found = True
            break

    return found


def compile_kernel(compile_nvidia: bool, is_uki: bool, jobs: int,
                   kver: str, local_src_dir: pathlib.PosixPath,
                   work_dir: pathlib.PosixPath, sign_kernel: bool,
                   system_name: str) -> None:
    """
    Compiles the kernel and any components based on user choice and copies over
    the compiled efi executable to user's local source directory.

    Args:
        compile_nvidia (bool): If True compiles nvidia drivers using portage against the new kernel.
        is_uki (bool): If True then signs the unified kernel image.
        kver (str): The name of the kernel version that is being compiled.
        local_src_dir (pathlib.PosixPath): The systems local source directory.
        output_file_path (pathlib.PosixPath): File path for the signed efi executable.
        work_dir (pathlib.PosixPath): The directory where the compilation is taking place.
        sign_kernel (bool): If True calls the sign_efi function to sign the kernel.
        system_name (str): The name of the system that the kernel is compiled for.

    Returns:
        output_file_path (pathlib.PosixPath): File path for the signed efi executable.
    """

    # Go into the work_dir.
    os.chdir(work_dir)

    # Compile kernel
    try:
        print(colorize(f"Compiling kernel {kver}...\n", colorama.Style.RESET_ALL))
        result = subprocess.run(["make", f"-j{jobs}"], check=True)
    except Exception as e:
        print(colorize(f"\nError compiling kernel {kver}: {e}", colorama.Fore.RED))
        sys.exit(1)

    # Install kernel modules to /lib/modules/.
    try:
        print(colorize(f"\nInstalling kernel modules for {kver}...\n", colorama.Style.RESET_ALL))
        result = subprocess.run(["make", "modules_install"], check=True)
    except Exception as e:
        print(colorize(f"\nError installing kernel modules for {kver}: {e}", colorama.Fore.RED))
        sys.exit(1)

    # Specify vmlinuz output directory.
    output_dir = local_src_dir / "vmlinuz"

    if is_uki:
        # Check if dracut is available.
        if not check_for_executable("dracut"):
            print(colorize("\nError: dracut was not found in your PATH. This is" \
                    "needed to generate an initramfs.", colorama.Fore.RED))
            sys.exit(1)

        # Set output path for initramfs cpio image.
        initramfs_path = local_src_dir / "initramfs" / f"initramfs-{system_name}.cpio"

        # Build initramfs
        try:
            print(colorize(f"\nBuilding initramfs for {kver}...\n", colorama.Style.RESET_ALL))
            result = subprocess.run(["dracut", "-f", f"--kver={kver}", initramfs_path], check=True)
        except Exception as e:
            print(colorize(f"\nError building initramfs for {kver}: {e}", colorama.Fore.RED))
            sys.exit(1)

        # Compile kernel with newly built initramfs cpio image.
        try:
            print(colorize(f"\nCompiling kernel {kver} with the newly built initramfs...\n", colorama.Style.RESET_ALL))
            result = subprocess.run(["make", f"-j{jobs}"], check=True)
        except Exception as e:
            print(colorize(f"\nError compiling kernel {kver}: {e}", colorama.Fore.RED))
            sys.exit(1)

        # Specify uki output directory.
        output_dir = local_src_dir / "uki"

    # Specify the path to copy the compiled efi executable to.
    output_file_path = output_dir / f"vmlinuz-{kver}.efi"
    
    # Specify the path to the bzImage.
    bzimage_path = work_dir / "arch" / "x86" / "boot" / "bzImage"

    # Sign the kernel if user has specified it.
    if sign_kernel:
        sign_efi(bzimage_path, is_uki, kver, output_file_path, work_dir)
    else:
        try:
            shutil.copyfile(bzimage_path, output_file_path)
            print(colorize(f"Copied vmlinuz-{kver}.efi to local source directory.",
                           colorama.Fore.GREEN))
        except Exception as e:
            print(colorize(f"Unknown error when copying vmlinuz-{kver}.efi to local \
                           source directory: {e}", colorama.Fore.RED))
            sys.exit(1)

    # Compile nvidia drivers against new compiled linux version.
    if compile_nvidia:
        # Specify default options for emerge to override whats in make.conf.
        env = os.environ.copy() # Dictionary of all current env variables.
        env["EMERGE_DEFAULT_OPTS"] = "--verbose" # Appends this environment variable to current env.

        try:
            print(colorize(f"\nCompiling nvidia drivers for {kver}...\n", colorama.Style.RESET_ALL))
            result = subprocess.run(["emerge", "x11-drivers/nvidia-drivers"],
                                    env=env, check=True)
        except Exception as e:
            print(colorize(f"\nError compiling nvidia drivers for {kver}: {e}", colorama.Fore.RED))
            sys.exit(1)

    return output_file_path


def sign_efi(bzimage_path: pathlib.PosixPath,
             is_uki: bool, kver:str,
             output_file_path: pathlib.PosixPath,
             work_dir: pathlib.PosixPath) -> pathlib.PosixPath:
    """
    Signs the compiled bzImage for use with secure boot.

    Args:
        bzimage_path (pathlib.PosixPath): File path for the bzImage in the work directory.
        is_uki (bool): If True then signs the unified kernel image.
        kver (str): The name of the kernel version that is being compiled.
        output_file_path (pathlib.PosixPath): File path for the signed efi executable.
        work_dir (pathlib.PosixPath): The directory where the compilation is taking place.

    Returns:
        None: This function does not return a value.
    """

    # Check if sbsign is available.
    if not check_for_executable("sbsign"):
        print(colorize("\nError: sbsign was not found in your PATH. This is" \
                "needed to sign the efi executable to be used with secure boot.",
                       colorama.Fore.RED))
        sys.exit(1)

    # Specify signature and certificate file paths.
    key_dir = pathlib.Path("/etc/keys/efikeys")
    db_key_path = key_dir / "db.key"
    db_crt_path = key_dir / "db.crt"

    # Check if db.key and db.crt exist.
    if not db_key_path.is_file():
        print(colorize(f"\nError: Can't find db.key, which is needed for" \
                "signing the kernel.", colorama.Fore.RED))
        print(colorize("It should be located in /etc/keys/efikeys/db.key.",
                       colorama.Fore.RED))
        sys.exit(1)
    elif not db_crt_path.is_file():
        print(colorize(f"\nError: Can't find db.crt, which is needed for signing the \
                       kernel.", colorama.Fore.RED))
        print(colorize("It should be located in /etc/keys/efikeys/db.crt.",
                       colorama.Fore.RED))
        sys.exit(1)

    # Sign the efi executable using sbsign.
    try:
        result = subprocess.run(["sbsign",
                                 "--key", db_key_path,
                                 "--cert", db_crt_path,
                                 "--output", output_file_path,
                                 bzimage_path], check=True)
        print(colorize(f"\nSigned kernel {kver}.",
                       colorama.Fore.GREEN))
    except Exception as e:
        print(colorize(f"\nError signing kernel {kver}: {e}", colorama.Fore.RED))
        sys.exit(1)

    return None


def install_kernel(efi_path: pathlib.PosixPath, is_uki: bool, kver: str,
                   system_name: str) -> None:
    """
    Installs kernel to the boot directory.

    Args:
        is_uki (bool): If True then signs the unified kernel image.
        kver (str): The name of the kernel version that is being compiled.
        efi_path (pathlib.PosixPath): File path for the signed efi executable.
        system_name (str): The name of the system that the kernel is compiled for.

    Returns:
        None: This function does not return a value.
    """

    # Specify the boot directory.
    boot_dir = pathlib.Path("/boot")
    boot_efi_dir = boot_dir / "efi" / "boot"
    boot_efi_path = boot_efi_dir / "bootx64.efi"

    # Create the boot directory if it doesn't exist.
    boot_dir.mkdir(parents=True, exist_ok=True)

    # Mount the boot directory.
    try:
        subprocess.run(["mount",boot_dir], check=True)
        print(colorize(f"Mounted {boot_dir}.",
                       colorama.Fore.GREEN))
    except Exception as e:
        print(colorize(f"Unknown error when mounting {boot_dir}: {e}",
                    colorama.Fore.RED))
        sys.exit(1)

    # Create the boot directory hierarchy if it doesn't exist.
    boot_efi_dir.mkdir(parents=True, exist_ok=True)

    # Copy the efi file to boot.
    try:
        shutil.copyfile(efi_path, boot_efi_path)
        print(colorize(f"Copied {kver} to boot!",
                       colorama.Fore.GREEN))
    except Exception as e:
        print(colorize(f"Unknown error when copying {kver} to boot: {e}",
                    colorama.Fore.RED))
        sys.exit(1)

    # Unmount the boot directory.
    try:
        subprocess.run(["umount",boot_dir], check=True)
        print(colorize(f"Unmounted {boot_dir}.",
                       colorama.Fore.GREEN))
    except Exception as e:
        print(colorize(f"Unknown error when unmounting {boot_dir}: {e}",
                    colorama.Fore.RED))
        sys.exit(1)

    # Success message
    print(colorize(f"Installed kernel {kver} for {system_name}.", colorama.Fore.GREEN))

    return None


def parse_arguments() -> argparse.Namespace:
    """
    Parse arguments that have been passed in the command line using the argparse
    library.

    Returns:
        args (argparse.Namespace): Command-line arguments parsed using argparse.
    """

    # Parse optional arguments.
    parser = argparse.ArgumentParser(description="Compiles, signs and installs user selected kernels.")
    parser.add_argument("--hostname", metavar="HOSTNAME", type=str,
                        default=socket.gethostname(),
                        help="hostname for the system that needs its kernel compiled.")
    parser.add_argument("-j","--jobs", metavar="JOBS", type=int, default=6,
                        help="specify the number of parallel jobs for compilation")
    parser.add_argument("-t", "--tmpfs", action="store_true",
                        help="compiles the kernel in a tmpfs directory (requires /etc/fstab configuration)")
    parser.add_argument("-u", "--uki", action="store_true",
                        help="compiles a unified kernel image (requires dracut)")
    parser.add_argument("-s", "--sign", action="store_true",
                        help="signs compiled efi executable (requires sbsign)")
    parser.add_argument("-i", "--install", action="store_true",
                        help="installs the compiled efi executable to /boot")
    parser.add_argument("-n", "--nvidia", action="store_true",
                        help="compiles and installs proprietary nvidia drivers alongside the new kernel (GENTOO ONLY!)")
    parser.add_argument("--nocolor", action="store_true",
                        help="disables colored output")
    args = parser.parse_args()

    return args


def main():
    """
    Compiles kernels for a specific system specified by the user. Then, based on
    command-line arguments, generates a UKI, signs it, and installs it to the
    boot directory. On gentoo the user has the option to compile the proprietary
    nvidia drivers against the newly built kernel.
    """

    # Global variables
    global no_color

    # Check if script is run as root.
    check_if_superuser()

    # Parse our command-line arguments.
    args = parse_arguments()
    compile_nvidia = args.nvidia
    is_uki = args.uki
    install = args.install
    jobs = args.jobs
    no_color = args.nocolor
    sign_kernel = args.sign
    system_name = args.hostname
    use_tmpfs = args.tmpfs

    # Obtain environmental variables.
    if os.getenv("NO_COLOR") == "1":
        no_color = True

    # Check if OS is Gentoo if user chose to compile nvidia drivers.
    if compile_nvidia:
        os_release_path = pathlib.Path("/etc/os-release")

        with open(os_release_path, "r") as file:
            for line in file:
                if line.startswith("NAME"):
                    line_list = line.split("=")
                    os_name = line_list[1].strip()

        if os_name != "Gentoo":
            print(colorize(f"Error: Compiling nvidia drivers for Non-Gentoo \
                    systems is not supported.", colorama.Fore.RED))
            sys.exit(1)

    # Check if the specified system's local kernel directory exists.
    local_src_dir = pathlib.Path(f"/usr/local/src/{system_name}")
    
    if not local_src_dir.is_dir():
        print(colorize(f"Error: {local_src_dir} does not exist.",
                       colorama.Fore.RED))
        sys.exit(1)

    # Show the avaiable kernels in the {local_src_dir}/linux/ directory.
    linux_dir = local_src_dir / "linux"
    print(colorize(f"Here is a list of available kernels for {system_name}:\n",
                   colorama.Style.RESET_ALL))

    # Create a list of available kernels based on what is found.
    kernels = []

    for ver in linux_dir.iterdir():
        if ver.is_dir():
            ver_name = ver.name
            kernels.append(ver_name)
    
    kernels = sorted(kernels, reverse=True)

    # Exit if there are no kernels available.
    if len(kernels) == 0:
        print(colorize(f"Error: No kernels were found in {linux_dir}.",
                       colorama.Fore.RED))
        sys.exit(1)
    
    # List out the available kernels with an item number associated with them.
    for inum, item in enumerate(kernels):
        print(colorize(f"{inum + 1}. {item}", colorama.Style.RESET_ALL))

    # Ask the user to choose a kernel version based on what was printed.
    while True:
        selection = input(colorize("\nPlease select a kernel version: ",
                                        colorama.Style.RESET_ALL)).strip()
        if selection.isdigit():
            selection = int(selection)
        else:
            print(colorize(f"\nInvalid selection: \"{selection}\"",
                           colorama.Fore.RED))
            print(colorize(f"Please enter an integer.", colorama.Fore.RED))
            continue

        if selection <= len(kernels):
            break
        else:
            print(colorize(f"\nInvalid selection: \"{selection}\"",
                           colorama.Fore.RED))
            print(colorize(f"Please try again.", colorama.Fore.RED))

    # Obtain the path for our chosen kernel version.
    linux_ver = kernels[selection - 1]
    linux_ver_num = linux_ver.replace("linux-","")
    kernel_dir = linux_dir / linux_ver

    # Find the value of CONFIG_LOCALVERSION.
    config_path = kernel_dir / ".config"

    with open(config_path, "r") as file:
        for line in file:
            if line.startswith("CONFIG_LOCALVERSION"):
                line_list = line.split("=")
                local_version = line_list[1].replace('"','').strip()
                local_version = local_version.replace("-", "", 1)

    # Specify the full kernel version name.
    kver = f"{linux_ver_num}-{local_version}"

    # If tmpfs has been specified mount the directory and copy our source files
    # over there.
    if use_tmpfs:
        tmpfs_dir = pathlib.Path(f"/var/tmp/linux/{system_name}")
        kernel_tmpfs_dir = tmpfs_dir / linux_ver
        work_dir = kernel_tmpfs_dir

        # Create the tmpfs directory if it doesn't exist.
        tmpfs_dir.mkdir(parents=True, exist_ok=True)

        # Try mounting the tmpfs directory if it isn't specified in fstab fail.
        try:
            subprocess.run(["mount", tmpfs_dir], check=True)
            print(colorize(f"Mounted tmpfs directory /var/tmp/linux/{system_name}.",
                           colorama.Fore.GREEN))
        except subprocess.CalledProcessError as e:
            print(colorize(f"Failed to mount {tmpfs_dir}: {e}",
                           colorama.Fore.RED))
            sys.exit(1)
        except Exception as e:
            print(colorize(f"Unknown error when mounting {tmpfs_dir}: {e}",
                           colorama.Fore.RED))
            sys.exit(1)

        # Copy our kernel_dir over to our tmpfs directory.
        try:
            shutil.copytree(kernel_dir, work_dir)
            print(colorize(f"Copied {kver} to {work_dir}.",
                           colorama.Fore.GREEN))
        except Exception as e:
            print(colorize(f"Error copying {kver} to {work_dir}: {e}",
                           colorama.Fore.RED))
            sys.exit(1)
    else:
        work_dir = kernel_dir

    # Change the /usr/src/linux symlink to our work_dir.
    linux_symlink = pathlib.Path("/usr/src/linux")

    if linux_symlink.is_symlink():
        linux_symlink.unlink()

    linux_symlink.symlink_to(work_dir)

    # Compile the kernel and obtain the output efi file path.
    efi_path = compile_kernel(compile_nvidia, is_uki, jobs, kver,
                              local_src_dir, work_dir, sign_kernel,
                              system_name)

    # Change the /usr/src/linux symlink to point to our kernel_dir.
    if linux_symlink.is_symlink():
        linux_symlink.unlink()

    linux_symlink.symlink_to(kernel_dir)
    print(colorize(f"Created /usr/src/linux symlink to {kver}.",
                   colorama.Fore.GREEN))

    # Unmount the tmpfs directory.
    if use_tmpfs:
        # Go into the kernel_dir.
        os.chdir(kernel_dir)

        # Remove the tmpfs work directory.
        try:
            shutil.rmtree(work_dir)
            print(colorize(f"Removed tmpfs work directory for {kver}.",
                           colorama.Fore.GREEN))
        except Exception as e:
            print(colorize(f"Error: unable to remove tmpfs work directory for {kver}",
                           colorama.Fore.RED))
            sys.exit(1)

        # Unmount the tmpfs directory.
        try:
            subprocess.run(["umount", tmpfs_dir], check=True)
            print(colorize(f"Unmounted tmpfs directory {tmpfs_dir}.",
                           colorama.Fore.GREEN))
        except subprocess.CalledProcessError as e:
            print(colorize(f"Failed to unmount {tmpfs_dir}: {e}",
                           colorama.Fore.RED))
            sys.exit(1)
        except Exception as e:
            print(colorize(f"Unknown error when unmounting {tmpfs_dir}: {e}",
                        colorama.Fore.RED))
            sys.exit(1)

    if install:
        install_kernel(efi_path, is_uki, kver, system_name)


if __name__ == "__main__":
    main()
