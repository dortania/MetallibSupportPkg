# MetallibSupportPkg

A collection of utilities related to patching Metal Libraries (`.metallib`) in macOS, specifically with the goal of restoring support for legacy hardware (namely Metal 3802-based GPUs on macOS Sequoia).

## Logic

MetallibSupportPkg houses the `metal_libraries` python library, which was developed to streamline Metal Library patching through the following:

1. Programmatically fetching the latest macOS Sequoia IPSW.
2. Extract the system volume DMG from the IPSW.
3. If the disk image is AEA encrypted, decrypt using [`aastuff`](https://github.com/dhinakg/aeota).
4. Mount the disk image, and extract all supported `.metallib` files.
5. Patch the `.metallib` files to support Metal 3802 GPUs.
6. Convert the directory into a macOS Distribution Package (PKG).

Notes regarding patching individual `.metallib` files:
1. Each `.metallib` is a collection of `.air` files.
2. Certain `.metallib` files are actually FAT Mach-O files. Thus they need to be thinned manually (Apple's `lipo` utility does not support the AIR64 architecture we need).
    - [metallib/patch.py: `_thin_file()`](./metal_libraries/metallib/patch.py#L218-L270)
3. Each `.metallib` file is actually a collection of `.air` files. Need to extract them using [zhouwei's format](https://github.com/zhuowei/MetalShaderTool).
    - [metallib/patch.py: `_unpack_metallib_to_air()`](./metal_libraries/metallib/patch.py#L127-L187)
4. `.air` files need to be next decompiled to `.ll` (LLVM IR) using Apple's `metal-objdump` utility.
    - [metallib/patch.py: `_decompile_air_to_ll()`](./metal_libraries/metallib/patch.py#L77-L109)
5. With the LLVM IR, we can begin patching the AIR version to v26 (compared to Sequoia's v27) as well as other necessary changes.
    - [metallib/patch.py: `_patch_ll()`](./metal_libraries/metallib/patch.py#L190-L215)
6. To compile IR to `.air`, we use Apple's `metal` utility.
    - [metallib/patch.py: `_recompile_ll_to_air()`](./metal_libraries/metallib/patch.py#L60-L74)
7. To pack each `.air` to a `.metallib` collection, we use Apple's `metallib` utility.
    - [metallib/patch.py: `_pack_air_to_metallib()`](./metal_libraries/metallib/patch.py#L112-L124)

Once finished, the resulting `.metallib` files should work with Metal 3802-based GPUs in macOS Sequoia.

## Usage

MetallibSupportPkg is not meant to be used by general users, the following is intended for developers.

Install the required dependencies:
```bash
python3 -m pip install -r requirements.txt
# Note Xcode is required to be installed for the `metal` and `metal-objdump` utilities
```

Fetch IPSW URL:
```bash
python3 metallib.py -d
# Example result: UniversalMac_15.0_24A5279h_Restore.ipsw
```

Extract system volume from IPSW:
```bash
python3 metallib.py -e <path_to_ipsw>
# Example result: 090-49684-056.dmg
```

Fetch Metal libraries from system volume, will extract to `15.x-<build>`:
```bash
python3 metallib.py -f <path_to_system_volume>
# Example result: 15.0-24A5279h
```

Patch Metal libraries:
```bash
# Directory containing the Metal libraries
python3 metallib.py -p <path_to_metallib_dir>
# Individual Metal library
python3 metallib.py -p <path_to_metallib>
```

Convert Metal libraries to macOS package:
```bash
python3 metallib.py -z <path_to_metallib_dir>
# Example result: MetallibSupportPkg-15.0-24A5279h.pkg
```

-----------

```
usage: metallib.py [-h] [-d] [-e EXTRACT] [-f FETCH] [-p PATCH] [-b BUILD_SYS_PATCH] [-z BUILD_PKG] [-c]

Download, extract, fetch, and patch Metal libraries.

options:
  -h, --help            show this help message and exit
  -d, --download        Download the latest IPSW.
  -e EXTRACT, --extract EXTRACT
                        Extract the system volume from an IPSW.
  -f FETCH, --fetch FETCH
                        Fetch Metal libraries from the system volume.
  -p PATCH, --patch PATCH
                        Patch Metal libraries.
  -b BUILD_SYS_PATCH, --build-sys-patch BUILD_SYS_PATCH
                        Build a system patch dictionary.
  -z BUILD_PKG, --build-pkg BUILD_PKG
                        Build a macOS package.
  -c, --continuous-integration
                        Run in continuous integration mode.
```