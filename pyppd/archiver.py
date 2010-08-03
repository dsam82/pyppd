import base64
import sys
import os
import fnmatch
import cPickle
import tarfile
import tempfile
from ppd import PPD
import lzma_proxy as lzma

def read_file_in_syspath(filename):
    """Reads the file in filename in each sys.path.

    If we couldn't find, throws the last IOError caught.

    """
    last_exception = None
    for path in sys.path:
        try:
            return open(path + "/" + filename).read()
        except IOError as ex:
            last_exception = ex
            continue
    raise last_exception

def find_files(directory, pattern):
    """Yields each file that matches pattern in directory."""
    abs_directory = os.path.abspath(directory)
    for root, dirnames, filenames in os.walk(abs_directory):
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)

def compress(directory):
    """Compresses and indexes all *.ppd files in directory returning as a string.

    The directory is walked recursively, inserting all ppds found in a tar file.
    For each, it parses and saves its name, description (in the format CUPS needs)
    and path into a dictionary, used as an index.
    Then, it compresses the tar file, adds into the dictionary as key ARCHIVE and
    string of all ppds concatenated and returns the pickle dump of the dictionary.

    """
    tmp = tempfile.NamedTemporaryFile()
    ppds = tarfile.open(fileobj = tmp.file, mode = 'w')
    ppds_index = {}

    for ppd_path in find_files(directory, "*.ppd"):
        try:
            ppd_file = open(ppd_path).read()
            ppds.add(ppd_path)

            # Removes the first slash in the path, so we can find the file in
            # the tar archive.
            ppd_path = ppd_path[1:]

            a_ppd = PPD(ppd_file)
            ppds_index[a_ppd.name] = (ppd_path, str(a_ppd))
        except:
            raise

    ppds_index['ARCHIVE'] = lzma.compress_file(tmp.name)
    ppds_pickle = lzma.compress(cPickle.dumps(ppds_index))
    ppds.close()

    return ppds_pickle

def create_archive(ppds_directory):
    """Returns a string with the decompressor, its dependencies and the archive.

    It reads the template at pyppd/pyppd-ppdfile.in, inserts the dependencies
    and the archive encoded in base64, and returns as a string.

    """
    ppds_compressed = base64.b64encode(compress(ppds_directory))

    template = read_file_in_syspath("pyppd/pyppd-ppdfile.in")
    lzma_proxy_py = read_file_in_syspath("pyppd/lzma_proxy.py")

    template = template.replace("@lzma_proxy@", lzma_proxy_py)
    template = template.replace("@ppds_compressed_b64@", ppds_compressed)

    return template
