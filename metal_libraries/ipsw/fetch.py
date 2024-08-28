"""
fetch.py: Fetch latest IPSW images for macOS
"""

import plistlib
import packaging.version

from .manifest import MetallibSupportPkgManifest

from ..network import NetworkUtilities
from .. import __version__

class FetchIPSW:

    def __init__(self, builds_to_ignore: list = [], minimum_version: str = "15") -> None:
        self._builds_to_ignore = builds_to_ignore
        self._minimum_version  = packaging.version.parse(minimum_version)


    def _fetch_apple_db_items(self) -> dict:
        """
        Get macOS installers from AppleDB
        """

        installers = [
            # "22F82": {
            #   url: "https://swcdn.apple.com/content/downloads/36/06/042-01917-A_B57IOY75IU/oocuh8ap7y8l8vhu6ria5aqk7edd262orj/InstallAssistant.pkg",
            #   version: "13.4.1",
            #   build: "22F82",
            # }
        ]

        apple_db = NetworkUtilities().get("https://api.appledb.dev/main.json")
        if apple_db is None:
            return installers

        apple_db = apple_db.json()
        for group in apple_db:
            if group != "ios":
                continue
            for item in apple_db[group]:
                if "osStr" not in item:
                    continue
                if item["osStr"] != "macOS":
                    continue
                if "build" not in item:
                    continue
                if "version" not in item:
                    continue
                if "sources" not in item:
                    continue

                if item["build"] in self._builds_to_ignore:
                    continue

                try:
                    if packaging.version.parse(item["version"].split(" ")[0]) < self._minimum_version:
                        continue
                except packaging.version.InvalidVersion:
                    continue

                # Skip 15.1 temporarily
                if item["version"].split(" ")[0] == "15.1":
                    continue

                name = "macOS"
                if "appledbWebImage" in item:
                    if "id" in item["appledbWebImage"]:
                        name += " " + item["appledbWebImage"]["id"]

                for source in item["sources"]:
                    if "links" not in source:
                        continue

                    hash = None
                    if "hashes" in source:
                        if "sha1" in source["hashes"]:
                            hash = source["hashes"]["sha1"]

                    for entry in source["links"]:
                        if "url" not in entry:
                            continue
                        if entry["url"].endswith(".ipsw") is False:
                            continue
                        if "preferred" in entry:
                            if entry["preferred"] is False:
                                continue

                        installers.append({
                            "Name":      name,
                            "Version":   item["version"],
                            "Build":     item["build"],
                            "URL":       entry["url"],
                            "Variant":   "Beta" if item["beta"] else "Public",
                            "Date":      item["released"],
                            "Hash":      hash,
                        })

        # Deduplicate builds
        installers = list({installer['Build']: installer for installer in installers}.values())

        # Reverse list
        installers = installers[::-1]

        return installers


    def _save_info(self, info: dict) -> None:
        """
        Save the build info to Info.plist
        """
        info["MetellibSupportPkgVersion"] = __version__
        with open("Info.plist", "wb") as file:
            plistlib.dump(info, file)


    def fetch(self) -> dict:
        """
        Fetch latest macOS installer
        """
        result = self._fetch_apple_db_items()
        if len(result) == 0:
            return {}
        MetallibSupportPkgManifest(result[0]).update_manifest()
        self._save_info(result[0])
        return result[0]["URL"]