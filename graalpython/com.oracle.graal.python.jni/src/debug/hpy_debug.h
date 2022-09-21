/* MIT License
 *
 * Copyright (c) 2022, Oracle and/or its affiliates.
 * Copyright (c) 2019 pyhandle
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#ifndef HPY_DEBUG_H
#define HPY_DEBUG_H

#include "hpy.h"

/*
  This is the main public API for the debug mode, and it's meant to be used
  by hpy.universal implementations (including but not limited to the
  CPython's version of hpy.universal which is included in this repo).

  The idea is that for every uctx there is a corresponding unique dctx which
  wraps it.

  If you call hpy_debug_get_ctx twice on the same uctx, you get the same
  result.

  IMPLEMENTATION NOTE: at the moment of writing, the only known user of the
  debug mode is CPython's hpy.universal: in that module, the uctx is a
  statically allocated singleton, so for simplicity of implementation
  currently we do the same inside debug_ctx.c, with a sanity check to ensure
  that we don't call hpy_debug_get_ctx with different uctxs. But this is a
  limitation of the current implementation and users should not rely on it. It
  is likely that we will need to change it in the future, e.g. if we want to
  have per-subinterpreter uctxs.
*/

HPyContext * hpy_debug_get_ctx(HPyContext *uctx);
int hpy_debug_ctx_init(HPyContext *dctx, HPyContext *uctx);
void hpy_debug_set_ctx(HPyContext *dctx);

// convert between debug and universal handles. These are basically
// the same as DHPy_open and DHPy_unwrap but with a different name
// because this is the public-facing API and DHPy/UHPy are only internal
// implementation details.
HPy hpy_debug_open_handle(HPyContext *dctx, HPy uh);
HPy hpy_debug_unwrap_handle(HPyContext *dctx, HPy dh);
void hpy_debug_close_handle(HPyContext *dctx, HPy dh);

// this is the HPy init function created by HPy_MODINIT. In CPython's version
// of hpy.universal the code is embedded inside the extension, so we can call
// this function directly instead of dlopen it. This is similar to what
// CPython does for its own built-in modules. But we must use the same
// signature as HPy_MODINIT

// Copied from Python's exports.h, pyport.h
#ifndef Py_EXPORTED_SYMBOL
    #if defined(_WIN32) || defined(__CYGWIN__)
        #define Py_EXPORTED_SYMBOL __declspec(dllexport)
    #else
        #define Py_EXPORTED_SYMBOL __attribute__ ((visibility ("default")))
    #endif
#endif
#ifdef ___cplusplus
extern "C"
#endif
Py_EXPORTED_SYMBOL
HPy HPyInit__debug(HPyContext *uctx);

#endif /* HPY_DEBUG_H */
