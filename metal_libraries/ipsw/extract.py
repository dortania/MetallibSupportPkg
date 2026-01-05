"""
extract.py: Extract System Volume from IPSW images
"""

import zipfile
import tempfile
import plistlib
import subprocess

from pathlib import Path

from ..utils.log import log


class IPSWExtract:

    def __init__(self, ipsw: str) -> None:
        self._ipsw = Path(ipsw)


    def _decrypt_aea(self, input: Path) -> str:
        """
        Decrypt an AEA file.
        """
        output = input.with_suffix("")
        aea_bin = Path(__file__).resolve().parent / "bins" / "aastuff"
        if not aea_bin.exists():
            raise FileNotFoundError(f"{aea_bin} not found")

        result = subprocess.run(
            [
                aea_bin,
                "--input",  input,
                "--output", output,
                "--decrypt-only",
                "--network"
            ],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            log(result)
            raise Exception(f"Failed to decrypt {input}")

        return output


    def _extract_system_volume(self) -> str:
        """
        Extract the system volume from an IPSW file.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(self._ipsw, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            with open(f"{tmp_dir}/BuildManifest.plist", "rb") as f:
                build_manifest = plistlib.load(f)

            system_image_path = None
            for build_identity in build_manifest["BuildIdentities"]:
                if build_identity["Ap,ProductType"] == "VirtualMac2,1":
                    system_image_path = build_identity["Manifest"]["OS"]["Info"]["Path"]
                    break

            if not system_image_path:
                raise Exception("Failed to find system image path")

            system_image_path = Path(tmp_dir, system_image_path)

            if system_image_path.suffix == ".aea":
                system_image_path = self._decrypt_aea(system_image_path)

            # Copy from tmp_dir to cwd
            result = subprocess.run(["/bin/cp", "-cr", system_image_path, "."], capture_output=True, text=True)
            if result.returncode != 0:
                log(result)
                raise Exception(f"Failed to copy {system_image_path}")


        return system_image_path.name


    def extract(self) -> str:
        """
        Extract the system volume from an IPSW file.
        """
        return self._extract_system_volume()