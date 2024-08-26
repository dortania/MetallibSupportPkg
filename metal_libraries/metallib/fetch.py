"""
fetch.py: Fetches all '.metallib' files from given path and backs them up.
"""

import plistlib
import subprocess

from pathlib import Path

from ..utils.log import log


class MetallibFetch:

    def __init__(self, input: str, output: str = None) -> None:
        self._input  = Path(input)
        self._output = Path(output) if output else self._build_output()


    def _known_broken_files(self) -> list[str]:
        """
        Known broken metallib files
        """
        return [
            # Error: The file was not recognized as a valid object file
            "/System/Library/PrivateFrameworks/GPUCompiler.framework/Versions/32023/Libraries/lib/clang", #/32023.335/lib/darwin/libtracepoint_rt_iosmac.metallib", # _Z22mesh_thread_tracepointPU11MTLconstantKjjDv3_jS1_j.air
            "/System/Library/PrivateFrameworks/GPUCompiler.framework/Versions/32023/Libraries/lib/clang", #/32023.335/lib/darwin/libtracepoint_rt_osx.metallib",    # _Z22mesh_thread_tracepointPU11MTLconstantKjjDv3_jS1_j.air
            "/System/Library/Frameworks/CoreImage.framework/CoreImage.metallib",                                                                                # _ZNK9coreimage7Sampler6extentEv.air
            "/System/Library/Frameworks/CoreImage.framework/Versions/A/CoreImage.metallib",                                                                     # _ZNK9coreimage7Sampler6extentEv.air

            # Error: multiple symbols ('memcpy')!
            "/System/Library/Frameworks/MLCompute.framework/Versions/A/Resources/default.metallib",

            # We crash metallib outright (memory error???)
            "/System/Library/Frameworks/MetalPerformanceShaders.framework/Versions/A/Frameworks/MPSCore.framework/Versions/A/Resources/default.metallib",
        ]


    def _build_output(self) -> Path:
        """
        Build the output path
        """
        version_file = Path(self._input, "System/Library/CoreServices/SystemVersion.plist")
        if not version_file.exists():
            raise Exception("SystemVersion.plist not found")

        version_data = plistlib.load(open(version_file, "rb"))
        version = version_data["ProductVersion"]
        build   = version_data["ProductBuildVersion"]

        return Path(f"{version}-{build}")


    def _fetch_files(self) -> list[Path]:
        """
        Fetch all metallib files
        """
        paths = [
            Path(self._input, "System/Library"),
            Path(self._input, "System/Applications"),
            Path(self._input, "System/iOSSupport"),
        ]
        files = []
        bad_files = self._known_broken_files()
        for path in paths:
            for file in path.rglob("**/*.metallib"):
                if "System/Library/Extensions" in str(file):
                    continue
                if file.is_symlink():
                    continue
                if any(bad_file in str(file) for bad_file in bad_files):
                    continue
                files.append(file)
        return files


    def _backup(self) -> Path:
        """
        Backup all metallib files
        """
        if self._output.exists():
            result = subprocess.run(["/bin/rm", "-rf", self._output], capture_output=True, text=True)
            if result.returncode != 0:
                log(result)
                raise Exception(f"Failed to remove {self._output}")
        self._output.mkdir(parents=True)

        for file in self._fetch_files():
            output = Path(self._output, file.relative_to(self._input))
            output.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(["/bin/cp", "-r", file, output], capture_output=True, text=True)
            if result.returncode != 0:
                log(result)
                raise Exception(f"Failed to copy {file} to {output}")

        return self._output


    def backup(self) -> Path:
        """
        Backup all metallib files
        """
        return self._backup()

