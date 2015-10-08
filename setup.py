import os
import shutil
import subprocess
from distutils.errors import LibError
from distutils.core import setup
from distutils.command.build import build as _build

AFL_UNIX_INSTALL_PATH = os.path.join("bin", "afl-unix")
AFL_UNIX_PATCH_FILE = os.path.join("patches", "afl-patch.diff")
AFL_CGC_INSTALL_PATH = os.path.join("bin", "afl-cgc")
SUPPORTED_ARCHES = ["aarch64", "x86_64", "i386", "arm", "ppc", "ppc64", "mips", "mips64"]

data_files = [ ]

# grab the afl-other-arch repo
if not os.path.exists(AFL_UNIX_INSTALL_PATH):
    AFL_UNIX_REPO = "git@git.seclab.cs.ucsb.edu:shellphish/afl-other-arch.git"
    if subprocess.call(['git', 'clone', AFL_UNIX_REPO, AFL_UNIX_INSTALL_PATH]) != 0:
        raise LibError("Unable to retrieve afl-unix")

    # apply the afl arm patch
    with open(AFL_UNIX_PATCH_FILE, "rb") as f:
        if subprocess.call(['patch', '-p0'], stdin=f, cwd=AFL_UNIX_INSTALL_PATH) != 0:
            raise LibError("Unable to apply AFL patch")

if not os.path.exists(AFL_CGC_INSTALL_PATH):
    AFL_CGC_REPO = "git@git.seclab.cs.ucsb.edu:cgc/driller-afl.git"
    if subprocess.call(['git', 'clone', AFL_CGC_REPO, AFL_CGC_INSTALL_PATH]) != 0:
        raise LibError("Unable to retrieve afl-cgc")

def _build_all():
    global data_files

    # build afls
    if subprocess.call(['./build.sh'] + SUPPORTED_ARCHES, cwd=AFL_UNIX_INSTALL_PATH) != 0:
        raise LibError("Unable to build afl-other-arch")

    if subprocess.call(['make'], cwd=AFL_CGC_INSTALL_PATH) != 0:
        raise LibError("Unable to make afl-cgc")

    if subprocess.call(['./build_qemu_support.sh'], cwd=os.path.join(AFL_CGC_INSTALL_PATH, "qemu_mode")) != 0:
        raise LibError("Unable to build afl-cgc-qemu")

    # grab libraries
    if subprocess.call(["./fetchlibs.sh"], cwd=".") != 0:
        raise LibError("Unable to fetch libraries")

    AFL_UNIX_FUZZ = os.path.join(AFL_UNIX_INSTALL_PATH)
    AFL_CGC_FUZZ  = os.path.join(AFL_CGC_INSTALL_PATH)

    # get data_files ready for exporting, probably a better way to do this
    data_files.append((AFL_UNIX_FUZZ, (os.path.join(AFL_UNIX_FUZZ, "afl-fuzz"))))
    data_files.append((AFL_CGC_FUZZ, (os.path.join(AFL_CGC_FUZZ, "afl-fuzz"))))

    for ARCH in SUPPORTED_ARCHES:
        TRACER_STR = os.path.join(AFL_UNIX_INSTALL_PATH, "tracers", ARCH)
        data_files.append((TRACER_STR, (os.path.join(TRACER_STR, "afl-qemu-trace"),),))

    # for each lib export it into 
    for LIB in os.listdir("libs"):
        OUTPUT_PATH = os.path.join("bin", "fuzzer-libs", LIB, "lib")
        INPUT_DIR = os.path.join("libs", LIB, "lib")
        for item in os.listdir(INPUT_DIR):
            print item
            # library directory transport everything
            if os.path.isdir(os.path.join(INPUT_DIR, item)):
                for library in os.listdir(os.path.join(INPUT_DIR, item)):
                    data_files.append((os.path.join(INPUT_DIR, item, library), os.path.join(OUTPUT_PATH, item, library)))
            else:
                data_files.append((os.path.join(INPUT_DIR, item), os.path.join(OUTPUT_PATH, item)))
                

    # add cgc
    TRACER_STR = os.path.join(AFL_CGC_INSTALL_PATH, "tracers", "i386")
    data_files.append((TRACER_STR, (os.path.join(TRACER_STR, "afl-qemu-trace"),),))

class build(_build):
    def run(self):
            self.execute(_build_all, (), msg="Building AFL and grabbing libraries")
            _build.run(self)
cmdclass = {'build': build}

setup(
    name='fuzzer', version='1.0', description="Python wrapper for multiarch AFL",
    packages=['fuzzer'],
    data_files=data_files,
    cmdclass=cmdclass,
    install_requires=['angr']
)
