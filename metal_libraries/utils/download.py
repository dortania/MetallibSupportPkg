"""
download.py
"""

import time
import hashlib

from pathlib import Path

from ..network import download, NetworkUtilities


class DownloadFile:

    def __init__(self, url: str) -> None:
        self._url = url


    def _download_item(self, url: str, expected_hash: str = None) -> str:
        name = Path(url).name

        # Check if URL is 404
        if NetworkUtilities(url).validate_link() is False:
            print(f"    {url} is a 404")
            raise Exception(f"{url} is a 404")

        download_obj = download.DownloadObject(url, name)
        download_obj.download()
        while download_obj.is_active():
            time.sleep(5)

        if not download_obj.download_complete:
            print("")
            print(f"Failed to download {name}")
            print(f"URL: {url}")
            raise Exception(f"Failed to download {name}")

        # Check if we downloaded an HTML file
        if not name.endswith("html"):
            # Check if content starts with '<!DOCTYPE html>'
            with open(name, "r") as f:
                try:
                    if f.read(15) == "<!DOCTYPE html>":
                        print(f"    {url} is a 404")
                        raise Exception(f"{url} is a 404")
                except UnicodeDecodeError:
                    pass

        if expected_hash:
            sha1 = hashlib.sha1()
            with open(name, "rb") as f:
                while True:
                    data = f.read(65536)
                    if not data:
                        break
                    sha1.update(data)

            if sha1.hexdigest() != expected_hash:
                print(f"  Hash mismatch for {name}")
                print(f"  Expected: {expected_hash}")
                print(f"  Got:      {sha1.hexdigest()}")
                raise Exception(f"Hash mismatch for {name}")

        return name


    def file(self) -> str:
        """
        Download file.
        """
        return self._download_item(self._url)