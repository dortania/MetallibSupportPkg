"""
patch_format.py: Generate a dictionary of system patches
"""

from pathlib import Path


class GenerateSysPatchDictionary:

    def __init__(self, directory: str) -> None:
        self._directory = Path(directory)


    def fetch_sys_patch_dict(self) -> str:
        """
        """
        sys_patch_dict = {
            "Install": {
                "/System/Library/Frameworks/CoreImage.framework/Versions/A": {
                    "CoreImage.metallib": "14.6.1"
                },
                "/System/Library/Frameworks/MetalPerformanceShaders.framework/Versions/A/Frameworks/MPSCore.framework/Versions/A/Resources": {
                    "default.metallib":   "14.6.1"
                },
            }
        }

        for metallib_file in self._directory.rglob("**/*.metallib"):
            parent_directory = Path("/") / metallib_file.parent.relative_to(self._directory)

            file = metallib_file.name
            value = self._directory.name

            if parent_directory in [
                "/System/Library/Frameworks/CoreImage.framework/Versions/A",
                "/System/Library/Frameworks/MetalPerformanceShaders.framework/Versions/A/Frameworks/MPSCore.framework/Versions/A/Resources",
            ]:
                continue

            if parent_directory not in sys_patch_dict["Install"]:
                sys_patch_dict["Install"][parent_directory] = {}

            sys_patch_dict["Install"][parent_directory][file] = value

        return sys_patch_dict


    def construct_sys_patch_dict(self) -> str:
        """
        """
        sys_patch_dict = self.fetch_sys_patch_dict()
        output = "{\n"
        for key, value in sys_patch_dict.items():
            output += f"    \"{key}\": {{\n"
            for sub_key, sub_value in value.items():
                output += f"        \"{sub_key}\": {{\n"
                for sub_sub_key, sub_sub_value in sub_value.items():
                    output += f"            \"{sub_sub_key}\": \"{sub_sub_value}\",\n"
                output += "        },\n"
            output += "    },\n"
        output += "}\n"

        return output