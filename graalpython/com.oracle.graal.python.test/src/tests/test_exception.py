# Copyright (c) 2018, Oracle and/or its affiliates.
# Copyright (C) 1996-2017 Python Software Foundation
#
# Licensed under the PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2

import unittest
import sys
import errno

class ExceptionTests(unittest.TestCase):

    def testInvalidTraceback(self):
        try:
            Exception().__traceback__ = 5
        except TypeError as e:
            self.assertIn("__traceback__ must be a traceback", str(e))
        else:
            self.fail("No exception raised")

    def testNoneClearsTracebackAttr(self):
        try:
            raise IndexError(4)
        except:
            tb = sys.exc_info()[2]

        e = Exception()
        e.__traceback__ = tb
        e.__traceback__ = None
        self.assertEqual(e.__traceback__, None)

    def testWithTraceback(self):
        try:
            raise IndexError(4)
        except:
            tb = sys.exc_info()[2]

        e = BaseException().with_traceback(tb)
        self.assertIsInstance(e, BaseException)
        # TODO this dosn't work yet
        #self.assertEqual(e.__traceback__, tb)

        e = IndexError(5).with_traceback(tb)
        self.assertIsInstance(e, IndexError)
        # TODO this dosn't work yet
        #self.assertEqual(e.__traceback__, tb)

        class MyException(Exception):
            pass

        e = MyException().with_traceback(tb)
        self.assertIsInstance(e, MyException)
        # TODO this dosn't work yet
        #self.assertEqual(e.__traceback__, tb)

    def test_aliases(self):
        self.assertTrue (IOError is OSError)
        self.assertTrue (EnvironmentError is OSError)

    def test_new_oserror(self):
        self.assertTrue(type(OSError(2)) is OSError)
        self.assertTrue(type(OSError(errno.EISDIR)) is OSError)
        self.assertTrue(type(OSError(2, "a message")) is FileNotFoundError)
        
        self.assertTrue(type(OSError(errno.EISDIR, "a message")) is IsADirectoryError)
        self.assertTrue(type(OSError(errno.EAGAIN, "a message")) is BlockingIOError)
        self.assertTrue(type(OSError(errno.EALREADY, "a message")) is BlockingIOError)
        self.assertTrue(type(OSError(errno.EINPROGRESS, "a message")) is BlockingIOError)
        self.assertTrue(type(OSError(errno.EWOULDBLOCK, "a message")) is BlockingIOError)
        self.assertTrue(type(OSError(errno.EPIPE, "a message")) is BrokenPipeError)
        self.assertTrue(type(OSError(errno.ESHUTDOWN, "a message")) is BrokenPipeError)
        self.assertTrue(type(OSError(errno.ECHILD, "a message")) is ChildProcessError)
        self.assertTrue(type(OSError(errno.ECONNABORTED, "a message")) is ConnectionAbortedError)
        self.assertTrue(type(OSError(errno.ECONNREFUSED, "a message")) is ConnectionRefusedError)
        self.assertTrue(type(OSError(errno.ECONNRESET, "a message")) is ConnectionResetError)
        self.assertTrue(type(OSError(errno.EEXIST, "a message")) is FileExistsError)
        self.assertTrue(type(OSError(errno.ENOENT, "a message")) is FileNotFoundError)
        self.assertTrue(type(OSError(errno.ENOTDIR, "a message")) is NotADirectoryError)
        self.assertTrue(type(OSError(errno.EINTR, "a message")) is InterruptedError)
        self.assertTrue(type(OSError(errno.EACCES, "a message")) is PermissionError)
        self.assertTrue(type(OSError(errno.EPERM, "a message")) is PermissionError)
        self.assertTrue(type(OSError(errno.ESRCH, "a message")) is ProcessLookupError)
        self.assertTrue(type(OSError(errno.ETIMEDOUT, "a message")) is TimeoutError)

    def test_oserror_empty_attributes(self):
        e = OSError(errno.EISDIR)
        self.assertEqual(e.errno, None)
        self.assertEqual(e.strerror, None)
        self.assertEqual(e.filename, None)
        self.assertEqual(e.filename2, None)

    def test_oserror_two_attributes(self):
        e = OSError(errno.EISDIR, "message")
        self.assertEqual(e.errno, 21)
        self.assertEqual(e.strerror, "message")
        self.assertEqual(e.filename, None)
        self.assertEqual(e.filename2, None)

    def test_oserror_four_attribute(self):
        e = OSError(errno.EISDIR, "message", "file1")
        self.assertEqual(e.errno, 21)
        self.assertEqual(e.strerror, "message")
        self.assertEqual(e.filename, "file1")
        self.assertEqual(e.filename2, None)

    def test_oserror_four_attribute(self):
        e = OSError(errno.EISDIR, "message", "file1", None, "file2")
        self.assertEqual(e.errno, 21)
        self.assertEqual(e.strerror, "message")
        self.assertEqual(e.filename, "file1")
        self.assertEqual(e.filename2, "file2")
