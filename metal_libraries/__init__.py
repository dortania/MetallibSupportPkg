"""
__init__.py: Entry Point for MetallibSupportPkg patching utilities
"""

__title__   = "metal_libraries"
__version__ = "1.0.0"
__author__  = "Dortania"
__url__     = "https://www.github.com/khronokernel/MetallibSupportPkg"


from .cli            import main

from .ipsw.fetch     import FetchIPSW
from .ipsw.extract   import IPSWExtract

from .metallib.fetch import MetallibFetch
from .metallib.patch import MetallibPatch

from .utils.log      import log
from .utils.download import DownloadFile