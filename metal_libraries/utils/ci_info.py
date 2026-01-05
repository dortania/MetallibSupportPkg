"""
ci_info.py: Get repository information
"""

import os

from ..network import NetworkUtilities


class CIInfo:

    def __init__(self) -> None:
        self._url = "https://api.github.com/repos/dortania/MetallibSupportPkg/releases?per_page=1000"


    def published_releases(self) -> list[str]:
        """
        Get the published releases
        """
        headers = {}
        if "GITHUB_TOKEN" in os.environ:
            headers = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}

        releases = NetworkUtilities().get(self._url, headers=headers)
        if releases is None:
            return []

        releases = releases.json()
        releases = [release["tag_name"] for release in releases]
        return [release.split("-")[1] for release in releases]