"""
fetch.py: Fetch latest IPSW images for macOS
"""

import plistlib
import packaging.version

from .manifest import MetallibSupportPkgManifest

from ..network import NetworkUtilities
from .. import __version__

class FetchIPSW:

    def __init__(self, builds_to_ignore: list = [], minimum_version: str = "15", maximum_version: str = "15.99.99") -> None:
        self._builds_to_ignore = builds_to_ignore
        self._minimum_version  = packaging.version.parse(minimum_version)
        self._maximum_version  = packaging.version.parse(maximum_version)


    def _fetch_apple_db_items(self):
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

        apple_db = NetworkUtilities().get("https://api.appledb.dev/ios/macOS/main.json")
        if apple_db is None:
            return []

        apple_db = apple_db.json()
        for item in apple_db:
            if item.get("internal") or item.get("rsr"):
                continue

            if "build" not in item or item["build"] in self._builds_to_ignore:
                continue

            try:
                version = packaging.version.parse(item["version"].split(" ")[0])
                if version < self._minimum_version or version > self._maximum_version:
                    continue
            except packaging.version.InvalidVersion:
                continue

            # We use MacPro7,1 to filter out any Apple silicon-only builds.
            if "MacPro7,1" not in item.get("deviceMap", []):
                continue

            name = "macOS"
            if "appledbWebImage" in item:
                if "id" in item["appledbWebImage"]:
                    name += " " + item["appledbWebImage"]["id"]

            for source in item.get("sources", []):
                # OTAs are unified, so MacPro7,1 and VirtualMac2,1 will be in the device map
                # IPSWs are not, so we only check for VirtualMac2,1
                if "VirtualMac2,1" not in source.get("deviceMap", []):
                    continue

                if source["type"] not in ["ipsw", "ota"]:
                    continue

                for link in source.get("links", []):
                    if not link["active"]:
                        continue

                    installers.append(
                        {
                            "Name": name,
                            "Version": item["version"],
                            "Type": source["type"],
                            "Build": item["build"],
                            "URL": link["url"],
                            "Variant": "Beta" if (item.get("beta") or item.get("rc")) else "Public",
                            "Date": item["released"],
                            "Hash": source.get("hashes", {}).get("sha1"),
                        }
                    )
                    # Don't process any other links
                    break
                else:
                    # If we didn't find any links, go to the next source
                    continue

                # We found a valid source, so don't check any other sources (so that we prefer IPSWs over OTAs)
                break

        # Deduplicate builds
        installers_by_build = {}
        for installer in installers:
            installers_by_build.setdefault(installer["Build"], []).append(installer)
        
        for build, installer_variants in installers_by_build.items():
            installer_variants.sort(key=lambda x: (x["Type"] != "ipsw", x["Variant"] != "Public"))
        
        deduplicated = [variants[0] for variants in installers_by_build.values()]
        deduplicated.sort(key=lambda x: x["Date"], reverse=True)

        return deduplicated


    def _save_info(self, info: dict) -> None:
        """
        Save the build info to Info.plist
        """
        info["MetallibSupportPkgVersion"] = __version__
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