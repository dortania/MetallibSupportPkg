"""
patch.py: Patches '.metallib' files with given patches.

-----------------------
Based on:
1. Jazzzny's 'pisser.py'
2. ASentientBot's 'bitcode edu 2.py'
3. zhouwei's 'unmetallib.py' (https://github.com/zhuowei/MetalShaderTools)
4. YuAo's MetalLibraryArchive (https://github.com/YuAo/MetalLibraryArchive)

-----------------------
Changes implemented:
1. Enforce '-mmacos-version-min=14.0' when recompiling .ll to .air
   - Resolves iOSSupport metallib compiling on Sequoia
2. Add support for thinning .metallib files
   - Resolves crashing on QuartzCore metallib
3. Add support for detecting non-AIR64 architectures
   - Resolves crashing on RenderBox metallib
4. Skip extracting and compiling empty .air files
   - Resolves crashing on CoreUI, VisualGeneration, Vision, Freeform and VectorKit

-----------------------
Manual steps:
1. Find all .metallib files in the system
2. Extract all .air files from each .metallib file
3. Decompile each .air file to .ll
4. Patch each .ll file
5. Recompile each .ll file to .air
6. Pack all .air files into a new .metallib file
"""

import re
import struct
import tempfile
import subprocess

from pathlib import Path
from typing import Optional

from ..utils.log import log


class MetallibPatch:

    def __init__(self) -> None:
        self._broken_file_map = {
            "metallib": {
                "/System/Library/PrivateFrameworks/VectorKit.framework/Versions/A/Resources/default.metallib": [
                    "Icon::shadow_vertex",
                ],
                "/System/Library/PrivateFrameworks/VFX.framework/Versions/A/Resources/default.metallib": [
                    "particle_quad_frag",
                ],
            },
            "air": {},
            "ll": {},
        }


    def _recompile_ll_to_air(self, input: str) -> str:
        """
        Convert from .ll to .air

        Returns:
        - Path to the recompiled .air
        """
        output = Path(input).with_suffix(".air")

        result = subprocess.run(["/usr/bin/xcrun", "metal", "-c", "-mmacos-version-min=14.0", input, "-o", output], capture_output=True, text=True)
        if result.returncode != 0:
            log(result)
            raise Exception(f"Failed to recompile {input}")

        return output


    def _decompile_air_to_ll(self, input: str) -> str:
        """
        Convert from .air to .ll

        Returns:
        - Path to the decompiled .ll
        """
        output = Path(input).with_suffix(".ll")

        result = subprocess.run(["/usr/bin/xcrun", "metal-objdump", "--disassemble", input], capture_output=True, text=True)
        if result.returncode != 0:
            log(result)
            raise Exception(f"Failed to decompile {input}")


        entry_point = None
        for line in result.stdout.splitlines():
            if "; ModuleID = " not in line:
                continue
            entry_point = line
            break

        assert(entry_point != None)

        with open(output, "w") as f:
            hit_entry = False
            for line in result.stdout.splitlines():
                if line == entry_point:
                    hit_entry = True
                if hit_entry is True:
                    f.write(f"{line}\n")

        return output


    def _pack_air_to_metallib(self, input_: list[str], output: str) -> str:
        """
        Pack .air files into a .metallib

        Returns:
        - Path to the packed .metallib
        """
        result = subprocess.run(["/usr/bin/xcrun", "metallib", *input_, "-o", output], capture_output=True, text=True)
        if result.returncode != 0:
            log(result)
            raise Exception(f"Failed to pack {input_} into {output}")

        return output


    def _unpack_metallib_to_air(self, input: str) -> list[tuple[str, bytes]]:
        """
        Unpack .metallib into .air files

        Returns:
        - List of tuples containing the function name and its contents
        """

        HEADER       = b"MTLB"
        TAG_NAME     = b"NAME"
        END_OF_TAG   = b"ENDT"
        BITCODE_SIZE = b"MDSZ"

        def u32(a: bytes, i: int) -> int:
            """
            Read a 32-bit unsigned integer from a byte array
            """
            return a[i] | a[i+1] << 8 | a[i+2] << 16 | a[i+3] << 24

        def u16(a: bytes, i: int) -> int:
            """
            Read a 16-bit unsigned integer from a byte array
            """
            return a[i] | a[i+1] << 8

        # Read the metallib file
        metallib_data = Path(input).read_bytes()
        # 2E000000
        if metallib_data[:4] != HEADER and metallib_data[4:8] != b"\x2E\x00\x00\x00":
            print(metallib_data[:4])
            raise Exception(f"Invalid metallib file: {input}")

        # Parse the metallib file for .air files
        directory_offset  = u32(metallib_data, 24)
        number_of_entries = u32(metallib_data, directory_offset)
        current_offset    = directory_offset + 4

        entries = []
        for i in range(number_of_entries):
            current_offset += 4
            while True:
                tag_type = metallib_data[current_offset:current_offset+4]
                if tag_type == END_OF_TAG:
                    current_offset += 4
                    break
                tag_length = u16(metallib_data, current_offset + 4)
                if tag_type == TAG_NAME:
                    entry_name = metallib_data[current_offset + 6:current_offset + 6 + tag_length - 1].decode("utf-8")
                elif tag_type == BITCODE_SIZE:
                    entry_size = u32(metallib_data, current_offset + 6)
                current_offset += 6 + tag_length
            entries.append((entry_name, entry_size))

        # Extract the .air files
        payload_offset = u32(metallib_data, 72)
        air_files = []
        for entry in entries:
            air_files.append((entry[0],metallib_data[payload_offset:payload_offset + entry[1]]))
            payload_offset += entry[1]

        return air_files


    def _patch_ll(self, input: str) -> None:
        """
        Patch AIR versioning to 2.6
        """
        def patch_line(line: str) -> str:
            if r'!{i32 2, i32 7, i32 0}' in line:
                return line.replace("i32 7", "i32 6")

            if r'!{!"Metal", i32 3, i32 2, i32 0}' in line:
                return line.replace("i32 2", "i32 1")

            if r'@__air_sampler_state' in line and r'[2 x i64]' in line:
                match = re.search(r"\[2 x i64\] \[i64 ([0-9]+), i64 0\]", line)
                if match:
                    return line.replace(match.group(0), f"i64 {match.group(1)}")
                return line.replace("[2 x i64]", "i64")

            return line

        ll_data = Path(input).read_text()
        for line in ll_data.splitlines():
            new_line = patch_line(line)
            if new_line != line:
                ll_data = ll_data.replace(line, new_line)

        Path(input).write_text(ll_data)


    def _thin_file(self, input: str) -> Optional[bytes]:
        """
        Thin metallib file

        Returns:
        - Thinned metallib file contents

        Reference:
        https://github.com/apple-oss-distributions/file/blob/file-96.100.2/file/src/readmacho.c
        """

        # https://docs.python.org/3/library/struct.html#format-strings
        FAT_HEADER_FORMAT = ">II"
        FAT_HEADER_SIZE = struct.calcsize(FAT_HEADER_FORMAT)
        FAT_ARCH_FORMAT = ">iiIII"
        FAT_ARCH_SIZE = struct.calcsize(FAT_ARCH_FORMAT)

        FAT_MAGIC = 0xCAFEBABE
        FAT_CIGAM = 0xBEBAFECA

        # Can support this in the future, but nothing in production supports it
        FAT_MAGIC_64 = 0xCAFEBABF
        FAT_CIGAM_64 = 0xBFBAFECA

        CPU_TYPE_APPLE_GPU = 0x1000013
        CPU_TYPE_AMD_GPU = 0x1000014
        CPU_TYPE_INTEL_GPU = 0x1000015
        CPU_TYPE_AIR64 = 0x1000017

        data = Path(str(input)).read_bytes()

        magic, architecture_count = struct.unpack_from(FAT_HEADER_FORMAT, data)
        if magic == FAT_MAGIC:
            pass
        elif magic == FAT_CIGAM:
            raise ValueError("Malformed FAT binary (FAT_CIGAM is not allowed)")
        elif magic == FAT_MAGIC_64:
            raise ValueError("64-bit FAT binaries are not currently supported")
        elif magic == FAT_CIGAM_64:
            raise ValueError("Malformed FAT binary (FAT_CIGAM_64 is not allowed)")
        else:
            return None

        fat_archs = data[FAT_HEADER_SIZE : FAT_HEADER_SIZE + architecture_count * FAT_ARCH_SIZE]

        for cpu_type, cpu_subtype, offset, size, align in struct.iter_unpack(FAT_ARCH_FORMAT, fat_archs):
            if cpu_type != CPU_TYPE_AIR64:
                continue

            air64_contents = data[offset : offset + size]
            return air64_contents

        return "DOES NOT CONTAIN AIR64 ARCHITECTURE"


    def patch(self, input: str, output: str) -> None:
        """
        Patch metallib
        """
        file = Path(input)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_output = Path(tmp)

            result = self._thin_file(file)
            if result:
                if result == "DOES NOT CONTAIN AIR64 ARCHITECTURE":
                    print("- Does not contain AIR64 architecture")
                    return
                # Change all future references to the thinned .metallib
                print("- Thinned .metallib")
                file = Path(tmp_output / file.name)
                file.write_bytes(result)

            print("- Unpacking into .air files")
            entries = self._unpack_metallib_to_air(file)
            for entry in entries:
                function_name = entry[0]
                contents = entry[1]
                if Path(tmp_output / function_name).exists():
                    raise
                if contents == b"":
                    continue

                is_broken = False
                if len(self._broken_file_map["metallib"]) > 0:
                    for key, value in self._broken_file_map["metallib"].items():
                        for function in value:
                            if function_name != function:
                                continue
                            if not str(file).endswith(key):
                                continue
                            print(f"  - Skipping {function_name} as it is known to be broken")
                            is_broken = True
                            break
                        if is_broken:
                            break
                if is_broken:
                    continue

                Path((tmp_output / function_name)).with_suffix(".air").write_bytes(contents)

            print("- Decompiling .air files to .ll")
            ll_files = []
            for air_file in Path(tmp_output).glob("*.air"):
                ll_file = self._decompile_air_to_ll(air_file)
                ll_files.append(ll_file)

            print("- Patching .ll files")
            for ll_file in ll_files:
                self._patch_ll(ll_file)

            print("- Recompiling .ll files to .air")
            air_files = []
            for ll_file in ll_files:
                air_file = self._recompile_ll_to_air(ll_file)
                air_files.append(air_file)

            if len(air_files) == 0:
                print("- No .air files to pack")
                return

            print("- Packing .air files to .metallib")
            self._pack_air_to_metallib(air_files, output)


    def _attempt_to_resolve_parent(self, file: Path) -> str:
        """
        Attempt to resolve the parent directory
        """
        parent_file = file
        attempts = 0
        while True:
            parent_file = parent_file.parent
            if parent_file.name.endswith(".framework") or parent_file.name.endswith(".app"):
                break
            if attempts > 5:
                return str(file)
            attempts += 1
        return parent_file.name


    def patch_all(self, input: str) -> None:
        """
        """
        for file in Path(input).rglob("**/*.metallib"):
            input = file
            output = file.with_suffix(".PATCHED")
            input_parent = self._attempt_to_resolve_parent(file)
            print(f"{'-' * 80}")
            print(f"Patching: {input_parent}'s {input.name}")
            self.patch(input, output)
            if output.exists():
                result = subprocess.run(["/bin/mv", output, input], capture_output=True, text=True)
                if result.returncode != 0:
                    log(result)
                    raise Exception(f"Failed to move {output} to {input}")
            else:
                # remove the input file if the output file does not exist
                result = subprocess.run(["/bin/rm", input], capture_output=True, text=True)
                if result.returncode != 0:
                    log(result)
                    raise Exception(f"Failed to remove {input}")