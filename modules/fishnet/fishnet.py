# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import division

import json
import time
import contextlib
import sys
import os
import stat
import platform
import ctypes

try:
    import httplib
except ImportError:
    import http.client as httplib

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

try:
    import urllib.request as urllib
except ImportError:
    import urllib


def stockfish_command(update=True):
    filename = stockfish_filename()

    if update:
        filename = update_stockfish(filename)

    return os.path.join(".", filename)


def stockfish_filename():
    machine = platform.machine().lower()

    modern, bmi2 = detect_cpu_capabilities()
    if modern and bmi2:
        suffix = "-bmi2"
    elif modern:
        suffix = "-modern"
    else:
        suffix = ""

    if os.name == "nt":
        return "stockfish-windows-%s%s.exe" % (machine, suffix)
    elif os.name == "os2" or sys.platform == "darwin":
        return "stockfish-osx-%s" % machine
    elif os.name == "posix":
        return "stockfish-%s%s" % (machine, suffix)


def update_stockfish(filename):
    print("Looking up %s ..." % filename)

    headers = {}
    headers["User-Agent"] = "Python-Puzzle-Generator"

    # Only update to newer versions
    try:
        headers["If-Modified-Since"] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(os.path.getmtime(filename)))
    except OSError:
        pass

    # Escape GitHub API rate limiting
    if "GITHUB_API_TOKEN" in os.environ:
        headers["Authorization"] = "token %s" % os.environ["GITHUB_API_TOKEN"]

    # Find latest release
    with http("GET", "https://api.github.com/repos/niklasf/Stockfish/releases/latest", headers=headers) as response:
        if response.status == 304:
            print("Local %s is newer than release" % filename)
            return filename

        release = json.loads(response.read().decode("utf-8"))

    print("Latest stockfish release is tagged", release["tag_name"])

    for asset in release["assets"]:
        if asset["name"] == filename:
            print("Found", asset["browser_download_url"])
            break
    else:
        raise ConfigError("No precompiled %s for your platform" % filename)

    # Download
    def reporthook(a, b, c):
        if sys.stderr.isatty():
            sys.stderr.write("\rDownloading %s: %d/%d (%d%%)" % (
                                 filename, min(a * b, c), c,
                                 round(min(a * b, c) * 100 / c)))
            sys.stderr.flush()

    urllib.urlretrieve(asset["browser_download_url"], filename, reporthook)

    sys.stderr.write("\n")
    sys.stderr.flush()

    # Make executable
    print("chmod +x", filename)
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)
    return filename


@contextlib.contextmanager
def make_cpuid():
    # Loosely based on cpuid.py by Anders Høst, licensed MIT:
    # https://github.com/flababah/cpuid.py

    # Prepare system information
    is_windows = os.name == "nt"
    is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
    if platform.machine().lower() not in ["amd64", "x86_64", "x86", "i686"]:
        raise OSError("Got no CPUID opcodes for %s" % platform.machine())

    # Struct for return value
    class CPUID_struct(ctypes.Structure):
        _fields_ = [("eax", ctypes.c_uint32),
                    ("ebx", ctypes.c_uint32),
                    ("ecx", ctypes.c_uint32),
                    ("edx", ctypes.c_uint32)]

    # Select kernel32 or libc
    if is_windows:
        if is_64bit:
            libc = ctypes.CDLL("kernel32.dll")
        else:
            libc = ctypes.windll.kernel32
    else:
        libc = ctypes.pythonapi

    # Select opcodes
    if is_64bit:
        if is_windows:
            # Windows x86_64
            # Two first call registers : RCX, RDX
            # Volatile registers       : RAX, RCX, RDX, R8-11
            opc = [
                0x53,                    # push   %rbx
                0x48, 0x89, 0xd0,        # mov    %rdx,%rax
                0x49, 0x89, 0xc8,        # mov    %rcx,%r8
                0x31, 0xc9,              # xor    %ecx,%ecx
                0x0f, 0xa2,              # cpuid
                0x41, 0x89, 0x00,        # mov    %eax,(%r8)
                0x41, 0x89, 0x58, 0x04,  # mov    %ebx,0x4(%r8)
                0x41, 0x89, 0x48, 0x08,  # mov    %ecx,0x8(%r8)
                0x41, 0x89, 0x50, 0x0c,  # mov    %edx,0xc(%r8)
                0x5b,                    # pop    %rbx
                0xc3                     # retq
            ]
        else:
            # Posix x86_64
            # Two first call registers : RDI, RSI
            # Volatile registers       : RAX, RCX, RDX, RSI, RDI, R8-11
            opc = [
                0x53,                    # push   %rbx
                0x48, 0x89, 0xf0,        # mov    %rsi,%rax
                0x31, 0xc9,              # xor    %ecx,%ecx
                0x0f, 0xa2,              # cpuid
                0x89, 0x07,              # mov    %eax,(%rdi)
                0x89, 0x5f, 0x04,        # mov    %ebx,0x4(%rdi)
                0x89, 0x4f, 0x08,        # mov    %ecx,0x8(%rdi)
                0x89, 0x57, 0x0c,        # mov    %edx,0xc(%rdi)
                0x5b,                    # pop    %rbx
                0xc3                     # retq
            ]
    else:
        # CDECL 32 bit
        # Two first call registers : Stack (%esp)
        # Volatile registers       : EAX, ECX, EDX
        opc = [
            0x53,                    # push   %ebx
            0x57,                    # push   %edi
            0x8b, 0x7c, 0x24, 0x0c,  # mov    0xc(%esp),%edi
            0x8b, 0x44, 0x24, 0x10,  # mov    0x10(%esp),%eax
            0x31, 0xc9,              # xor    %ecx,%ecx
            0x0f, 0xa2,              # cpuid
            0x89, 0x07,              # mov    %eax,(%edi)
            0x89, 0x5f, 0x04,        # mov    %ebx,0x4(%edi)
            0x89, 0x4f, 0x08,        # mov    %ecx,0x8(%edi)
            0x89, 0x57, 0x0c,        # mov    %edx,0xc(%edi)
            0x5f,                    # pop    %edi
            0x5b,                    # pop    %ebx
            0xc3                     # ret
        ]

    code_size = len(opc)
    code = (ctypes.c_ubyte * code_size)(*opc)

    if is_windows:
        # Allocate executable memory
        addr = libc.VirtualAlloc(None, code_size, 0x1000, 0x40)
        if not addr:
            raise MemoryError("Could not VirtualAlloc RWX memory")
    else:
        # Allocate memory
        libc.valloc.restype = ctypes.c_void_p
        libc.valloc.argtypes = [ctypes.c_size_t]
        addr = libc.valloc(code_size)
        if not addr:
            raise MemoryError("Could not valloc memory")

        # Make executable
        libc.mprotect.restype = ctypes.c_int
        libc.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
        if 0 != libc.mprotect(addr, code_size, 1 | 2 | 4):
            raise OSError("Failed to set RWX using mprotect")

    # Copy code to allocated executable memory. No need to flush instruction
    # cache for CPUID.
    ctypes.memmove(addr, code, code_size)

    # Create and yield callable
    result = CPUID_struct()
    func_type = ctypes.CFUNCTYPE(None, ctypes.POINTER(CPUID_struct), ctypes.c_uint32)
    func_ptr = func_type(addr)

    def cpuid(eax):
        func_ptr(result, eax)
        return result.eax, result.ebx, result.ecx, result.edx

    yield cpuid

    # Free
    if is_windows:
        libc.VirtualFree(addr, 0, 0x8000)
    else:
        libc.free.restype = None
        libc.free.argtypes = [ctypes.c_void_p]
        libc.free(addr)


def detect_cpu_capabilities():
    # Detects support for popcnt and pext instructions
    modern, bmi2 = False, False

    try:
        with make_cpuid() as cpuid:
            for eax in [0x0, 0x80000000]:
                highest, _, _, _ = cpuid(eax)
                for eax in range(eax, highest + 1):
                    a, b, c, d = cpuid(eax)

                    # popcnt
                    if eax == 1 and c & (1 << 23):
                        modern = True

                    # pext
                    if eax == 7 and b & (1 << 8):
                        bmi2 = True
    except OSError:
        pass

    return modern, bmi2


class HttpError(Exception):
    def __init__(self, status, reason, body):
        self.status = status
        self.reason = reason
        self.body = body

    def __str__(self):
        return "HTTP %d %s\n\n%s" % (self.status, self.reason, self.body)

    def __repr__(self):
        return "%s(%d, %r, %r)" % (type(self).__name__, self.status,
                                   self.reason, self.body)


class HttpServerError(HttpError):
    pass


class HttpClientError(HttpError):
    pass


@contextlib.contextmanager
def http(method, url, body=None, headers=None):
    url_info = urlparse.urlparse(url)
    if url_info.scheme == "https":
        con = httplib.HTTPSConnection(url_info.hostname, url_info.port or 443)
    else:
        con = httplib.HTTPConnection(url_info.hostname, url_info.port or 80)

    con.request(method, url_info.path, body, headers)
    response = con.getresponse()

    try:
        if 400 <= response.status < 500:
            raise HttpClientError(response.status, response.reason,
                                  response.read())
        elif 500 <= response.status < 600:
            raise HttpServerError(response.status, response.reason,
                                  response.read())
        else:
            yield response
    finally:
        con.close()
