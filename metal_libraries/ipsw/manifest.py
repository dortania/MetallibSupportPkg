"""
manifest.py: Generate manifest.json for MetallibSupportPkg API
"""

import json

from pathlib  import Path
from datetime import datetime

from ..network import NetworkUtilities


METALLIB_API_LINK = "https://dortania.github.io/MetallibSupportPkg/manifest.json"


class MetallibSupportPkgManifest:

    def __init__(self, latest_ipsw: dict) -> None:
        """
        latest_ipsw: dict

        {
            "Name": "macOS Sequoia",
            "Version": "15.0 beta 7",
            "Build": "24A5327a",
            "URL": "https://updates.cdn-apple.com/2024SummerSeed/fullrestores/062-64520/F98C92F6-656A-46BB-A1DB-F447698DBB72/UniversalMac_15.0_24A5327a_Restore.ipsw",
            "Variant": "Beta",
            "Date": "2024-08-20",
            "Hash": "6402881ec02bee6a7340237517c0872739b42820"
        }
        """
        self._latest_ipsw = latest_ipsw


    def _generate_item_manifest(self) -> dict:
        """
        Generate manifest.json for MetallibSupportPkg API
        """
        version = self._latest_ipsw["Version"]
        if " " in version:
            version = version.split(" ")[0]
        manifest = {
            "build":     self._latest_ipsw["Build"],
            "version":   version,
            "date":      self._latest_ipsw['Date'],
            "sha1sum":   self._latest_ipsw["Hash"],
            "name":      f"MetallibSupportPkg {self._latest_ipsw['Version']} build {self._latest_ipsw['Build']}",
            "seen":      datetime.now().strftime("%Y-%m-%d"),
            "url":       f"https://github.com/dortania/MetallibSupportPkg/releases/download/{version}-{self._latest_ipsw['Build']}/MetallibSupportPkg-{version}-{self._latest_ipsw['Build']}.pkg",
        }

        return manifest


    def update_manifest(self) -> None:
        """
        Update manifest.json for MetallibSupportPkg API
        """
        data = self._generate_item_manifest()

        # Fetch current manifest
        try:
            current_manifest = NetworkUtilities().get(METALLIB_API_LINK).json()
        except:
            current_manifest = []

        # Check if empty
        if not current_manifest:
            current_manifest = []

        # Check if item already exists
        for item in current_manifest:
            if item["build"] == data["build"]:
                return

        # Add new item
        current_manifest.append(data)

        # Sort by date
        current_manifest = sorted(current_manifest, key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d"), reverse=True)

        # Create deploy directory
        Path("deploy").mkdir(exist_ok=True)

        # Write manifest
        with open("deploy/manifest.json", "w") as f:
            json.dump(current_manifest, f, indent=4)

