"""
mount.py: Mount a DMG file
"""


import os
import tempfile
import subprocess


class MountDMG:
    def __init__(self, dmg_path):
        self.dmg_path = dmg_path

    def __enter__(self):
        self.mount_point = tempfile.mkdtemp()
        subprocess.check_call(['/usr/bin/hdiutil', 'attach', '-mountpoint', self.mount_point, self.dmg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return self.mount_point

    def __exit__(self, exc_type, exc_value, traceback):
        subprocess.check_call(['/usr/bin/hdiutil', 'detach', self.mount_point], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.rmdir(self.mount_point)