# Copyright (c) 2019, 2023, Oracle and/or its affiliates. All rights reserved.
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
#
# The Universal Permissive License (UPL), Version 1.0
#
# Subject to the condition set forth below, permission is hereby granted to any
# person obtaining a copy of this software, associated documentation and/or
# data (collectively the "Software"), free of charge and under any and all
# copyright rights in the Software, and any and all patent rights owned or
# freely licensable by each licensor hereunder covering either (i) the
# unmodified Software as contributed to or provided by such licensor, or (ii)
# the Larger Works (as defined below), to deal in both
#
# (a) the Software, and
#
# (b) any piece of software and/or hardware listed in the lrgrwrks.txt file if
# one is included with the Software each a "Larger Work" to which the Software
# is contributed by such licensors),
#
# without restriction, including without limitation the rights to copy, create
# derivative works of, display, perform, and distribute the Software and make,
# use, sell, offer for sale, import, export, have made, and have sold the
# Software and the Larger Work(s), and to sublicense the foregoing rights on
# either these or other terms.
#
# This license is subject to the following condition:
#
# The above copyright notice and either this complete permission notice or at a
# minimum a reference to the UPL must be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from sys import meta_path
WARNED = False


class PipImportHook:
    @staticmethod
    def print_version_warning():
        global WARNED
        if not WARNED:
            from warnings import warn
            warn("You are using an untested version of pip. GraalPy " +
                 "provides patches and workarounds for a number of packages when used with " +
                 "compatible pip versions. We recommend to stick with the pip version that " +
                 "ships with this version of GraalPy.", RuntimeWarning)
            WARNED = True

    @staticmethod
    def _check_patched_pip(fullname, path, target):
        from os.path import join, exists
        for finder in meta_path:
            if finder is PipImportHook:
                continue
            real_spec = finder.find_spec(fullname, path, target)
            if real_spec:
                search_locations = getattr(real_spec, 'submodule_search_locations', [])
                for location in search_locations:
                    path_to_check = join(location, '_internal', 'utils', 'graalpy.py')
                    if exists(path_to_check):
                        return
                PipImportHook.print_version_warning()

    @staticmethod
    def find_spec(fullname, path, target=None):
        if fullname == "pip":
            PipImportHook._check_patched_pip(fullname, path, target)


meta_path.insert(0, PipImportHook)
