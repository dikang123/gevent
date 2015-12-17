from __future__ import print_function
import sys
import subprocess
import unittest
from gevent.thread import allocate_lock

script = """
from gevent import monkey
monkey.patch_all()
import sys, os, threading, time


# A deadlock-killer, to prevent the
# testsuite to hang forever
def killer():
    time.sleep(0.1)
    sys.stdout.write('..program blocked; aborting!')
    sys.stdout.flush()
    os._exit(2)
t = threading.Thread(target=killer)
t.daemon = True
t.start()


def trace(frame, event, arg):
    if threading is not None:
        threading.currentThread()
    return trace


def doit():
    sys.stdout.write("..thread started..")


def test1():
    t = threading.Thread(target=doit)
    t.start()
    t.join()
    sys.settrace(None)

sys.settrace(trace)
if len(sys.argv) > 1:
    test1()

sys.stdout.write("..finishing..")
"""


class TestTrace(unittest.TestCase):
    def test_untraceable_lock(self):
        if hasattr(sys, 'gettrace'):
            old = sys.gettrace()
        else:
            old = None
        PYPY = hasattr(sys, 'pypy_version_info')
        lst = []
        try:
            def trace(frame, ev, arg):
                lst.append((frame.f_code.co_filename, frame.f_lineno, ev))
                if not PYPY:
                    print("TRACE: %s:%s %s" % lst[-1])
                return trace

            with allocate_lock():
                sys.settrace(trace)
        finally:
            sys.settrace(old)

        if not PYPY:
            self.assertEqual(lst, [], "trace not empty")
        else:
            # Have an assert so that we know if we miscompile
            self.assertTrue(len(lst) > 0, "should not compile on pypy")

    def run_script(self, more_args=()):
        args = [sys.executable, "-c", script]
        args.extend(more_args)
        rc = subprocess.call(args)
        self.assertNotEqual(rc, 2, "interpreter was blocked")
        self.assertEqual(rc, 0, "Unexpected error")

    def test_finalize_with_trace(self):
        self.run_script()

    def test_bootstrap_inner_with_trace(self):
        self.run_script(["1"])


if __name__ == "__main__":
    import greentest
    greentest.main()
