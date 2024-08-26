"""
cli.py: Command Line Interface for MetallibSupportPkg patching utilities
"""

import argparse
import macos_pkg_builder

from pathlib import Path

from .                   import __version__, __url__
from .ipsw.fetch         import FetchIPSW
from .ipsw.extract       import IPSWExtract
from .metallib.fetch     import MetallibFetch
from .metallib.patch     import MetallibPatch
from .utils.download     import DownloadFile
from .utils.mount        import MountDMG
from .utils.ci_info      import CIInfo
from .utils.patch_format import GenerateSysPatchDictionary


def download(ci: bool = False) -> str:
    """
    Fetches and downloads latest IPSW

    Parameters:
    - ci: boolean, if True, fetches the latest IPSW for CI

    Returns:
    - IPSW file path
    """
    builds_to_ignore = []
    if ci is True:
        builds_to_ignore = CIInfo().published_releases()
    url = FetchIPSW(builds_to_ignore).fetch()
    file = DownloadFile(url).file()
    return file

def extract(input: str) -> str:
    """
    Extracts the system volume DMG from an IPSW

    Parameters:
    - input: str, path to the IPSW file

    Returns:
    - path to the extracted system volume
    """
    return IPSWExtract(input).extract()


def fetch(input: str = "/", output: str = None) -> str:
    """
    Fetches all .metallib files from a given path
    If a DMG is provided, it will be mounted and unmounted

    Parameters:
    - input: str, path to the system volume or DMG
    - output: str, path to the output directory

    Returns:
    - path to the output directory
    """
    if input.endswith(".dmg"):
        with MountDMG(input) as mount_point:
            return MetallibFetch(mount_point, output).backup()
    return MetallibFetch(input, output).backup()


def patch(input: str = "/") -> None:
    """
    Patches all .metallib files in a given path

    Parameters:
    - input: str, path to the system volume or DMG

    Returns:
    - None
    """
    if Path(input).is_dir():
        MetallibPatch().patch_all(input)
    else:
        MetallibPatch().patch(input, input)


def build_pkg(input: str) -> None:
    """
    Builds a macOS package from a given directory
    """
    name = Path(input).name
    assert macos_pkg_builder.Packages(
        pkg_output=f"MetallibSupportPkg-{name}.pkg",
        pkg_bundle_id=f"com.dortania.metallibsupportpkg.{name}",
        pkg_version=__version__,
        pkg_file_structure={
            input: f"/Library/Application Support/Dortania/MetallibSupportPkg/{name}"
        },
        pkg_welcome=f"# MetallibSupportPkg\n\nThis package installs patched Metal Libraries for usage with OpenCore Legacy Patcher specifically targeting Macs with Metal 3802-based Graphics cards on macOS 15, Sequoia and newer.\n\nAffected graphics card models:\n\n* Intel Ivy Bridge and Haswell iGPUs\n* Nvidia Kepler dGPUs\n\n----------\nInstall destination:\n\n* `/Library/Application Support/Dortania/MetallibSupportPkg/{Path(input).name}`\n\n----------\n\nFor more information, see the [MetallibSupportPkg repository]({__url__}).",
        pkg_title=f"MetallibSupportPkg for {name}",
        pkg_as_distribution=True
    ).build() is True
    print(f"MetallibSupportPkg-{name}.pkg")


def build_sys_patch(input: str, ci: bool = False) -> None:
    """
    Builds a system patch dictionary
    """
    result = GenerateSysPatchDictionary(input).construct_sys_patch_dict()
    if ci is True:
        with open("sys_patch_dict.py", "w") as f:
            f.write(result)
    else:
        print(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download, extract, fetch, and patch Metal libraries.")
    parser.add_argument("-d", "--download",               action="store_true", help="Download the latest IPSW.")
    parser.add_argument("-e", "--extract",                type=str,            help="Extract the system volume from an IPSW.")
    parser.add_argument("-f", "--fetch",                  type=str,            help="Fetch Metal libraries from the system volume.")
    parser.add_argument("-p", "--patch",                  type=str,            help="Patch Metal libraries.")
    parser.add_argument("-b", "--build-sys-patch",        type=str,            help="Build a system patch dictionary.")
    parser.add_argument("-z", "--build-pkg",              type=str,            help="Build a macOS package.")
    parser.add_argument("-c", "--continuous-integration", action="store_true", help="Run in continuous integration mode.")

    args = parser.parse_args()

    if args.download:
        print(download(args.continuous_integration))
    elif args.extract:
        print(extract(args.extract))
    elif args.fetch:
        print(fetch(args.fetch))
    elif args.patch:
        patch(args.patch)
    elif args.build_sys_patch:
        build_sys_patch(args.build_sys_patch, args.continuous_integration)
    elif args.build_pkg:
        build_pkg(args.build_pkg)
    else:
        parser.print_help()