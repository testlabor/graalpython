# Copyright (c) 2020, 2022, Oracle and/or its affiliates. All rights reserved.
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

import mx
import mx_benchmark

import glob
import json
import math
import os
import shutil
import subprocess
import sys

from os.path import join, abspath, exists


SUITE = None
python_vm_registry = None

DEFAULT_NUMPY_BENCHMARKS = [
    "bench_app",
    "bench_core",
    # "bench_function_base",
    "bench_indexing",
    # "bench_io",
    "bench_linalg",
    # "bench_ma",
    # "bench_random",
    "bench_reduce",
    # "bench_shape_base",
    # "bench_ufunc",
]

DEFAULT_PYPERFORMANCE_BENCHMARKS = [
    # "2to3",
    # "chameleon",
    "chaos",
    # "crypto_pyaes",
    # "django_template",
    # "dulwich_log",
    "fannkuch",
    "float",
    "go",
    "hexiom",
    # "html5lib",
    "json_dumps",
    "json_loads",
    "logging",
    # "mako",
    "meteor_contest",
    "nbody",
    "nqueens",
    "pathlib",
    "pickle",
    "pickle_dict",
    "pickle_list",
    "pickle_pure_python",
    "pidigits",
    "pyflate",
    "regex_compile",
    "regex_dna",
    "regex_effbot",
    "regex_v8",
    "richards",
    "scimark",
    "spectral_norm",
    # "sqlalchemy_declarative",
    # "sqlalchemy_imperative",
    # "sqlite_synth",
    "sympy",
    "telco",
    "tornado_http",
    "unpack_sequence",
    "unpickle",
    "unpickle_list",
    "unpickle_pure_python",
    "xml_etree",
]

DEFAULT_PYPY_BENCHMARKS = [
    "ai",
    # "bm_chameleon",
    "bm_dulwich_log",
    "bm_mako",
    "bm_mdp",
    "chaos",
    # "cpython_doc",
    "crypto_pyaes",
    "deltablue",
    "django",
    "eparse",
    "fannkuch",
    "float",
    "genshi_text",
    "genshi_xml",
    "go",
    "hexiom2",
    "html5lib",
    "json_bench",
    "meteor-contest",
    "nbody_modified",
    "nqueens",
    "pidigits",
    "pyflate-fast",
    "pyxl_bench",
    "raytrace-simple",
    "richards",
    "scimark_fft",
    "scimark_lu",
    "scimark_montecarlo",
    "scimark_sor",
    "scimark_sparsematmult",
    "spectral-norm",
    "spitfire2",
    "spitfire_cstringio2",
    # "sqlalchemy_declarative",
    # "sqlalchemy_imperative",
    # "sqlitesynth",
    # "sympy_expand",
    # "sympy_integrate",
    # "sympy_str",
    # "sympy_sum",
    # "telco",
    # "twisted_names",
    # "twisted_pb",
    # "twisted_tcp",
]


class PyPerfJsonRule(mx_benchmark.Rule):
    """Parses a JSON file produced by PyPerf and creates a measurement result."""

    def __init__(self, filename: str, suiteName: str):
        self.filename = filename
        self.suiteName = suiteName

    def parse(self, text: str) -> dict:
        r = []
        with open(self._prepend_working_dir(self.filename)) as fp:
            js = json.load(fp)
            benchmarks = js["benchmarks"]
            for benchmark in benchmarks:
                name = benchmark.get("metadata", js["metadata"])["name"]
                for run in benchmark["runs"]:
                    if values := run.get("values", None):
                        warmups = run.get("warmups", [])
                        for idx, warmup in enumerate(warmups):
                            r.append(
                                {
                                    "bench-suite": self.suiteName,
                                    "benchmark": name,
                                    "metric.name": "warmup",
                                    "metric.unit": "ms",
                                    "metric.score-function": "id",
                                    "metric.better": "lower",
                                    "metric.type": "numeric",
                                    "metric.iteration": idx,
                                    "metric.value": warmup[1],  # 0 is inner_loop count
                                }
                            )
                        for value in values:
                            r.append(
                                {
                                    "bench-suite": self.suiteName,
                                    "benchmark": name,
                                    "metric.name": "time",
                                    "metric.unit": "ms",
                                    "metric.score-function": "id",
                                    "metric.better": "lower",
                                    "metric.type": "numeric",
                                    "metric.iteration": 0,
                                    "metric.value": value,
                                }
                            )
                        if maxrss := run["metadata"].get(
                            "mem_max_rss", js["metadata"].get("mem_max_rss", 0)
                        ):
                            r.append(
                                {
                                    "bench-suite": self.suiteName,
                                    "benchmark": name,
                                    "metric.name": "max-rss",
                                    "metric.unit": "B",
                                    "metric.score-function": "id",
                                    "metric.better": "lower",
                                    "metric.type": "numeric",
                                    "metric.iteration": 0,
                                    "metric.value": maxrss,
                                }
                            )

        return r


class AsvJsonRule(mx_benchmark.Rule):
    """Parses a JSON file produced by ASV (airspeed-velocity) and creates a measurement result."""

    def __init__(self, filename: str, suiteName: str):
        self.filename = filename
        self.suiteName = suiteName

    def parse(self, text: str) -> dict:
        import itertools

        r = []
        with open(self._prepend_working_dir(self.filename)) as fp:
            js = json.load(fp)

            columns = js["result_columns"]  # type: list[str]
            peak_idx = columns.index("result")
            param_idx = columns.index("params")
            try:
                samples_idx = columns.index("samples")
            except ValueError:
                samples_idx = -1

            for benchmark, result in js["results"].items():
                param_combinations = itertools.product(*result[param_idx])
                for run_idx, params in enumerate(param_combinations):
                    value = result[peak_idx][run_idx]
                    if not value or math.isnan(value):
                        continue
                    r.append(
                        {
                            "bench-suite": self.suiteName,
                            "benchmark": benchmark,
                            "metric.name": "time",
                            "metric.unit": "s",
                            "metric.score-function": "id",
                            "metric.better": "lower",
                            "metric.type": "numeric",
                            "metric.iteration": 0,
                            "metric.value": value,
                            "config.run-flags": " ".join(params),
                        }
                    )
                    if samples_idx >= 0:
                        for iteration, value in enumerate(result[samples_idx][run_idx]):
                            r.append(
                                {
                                    "bench-suite": self.suiteName,
                                    "benchmark": benchmark,
                                    "metric.name": "warmup",
                                    "metric.unit": "s",
                                    "metric.score-function": "id",
                                    "metric.better": "lower",
                                    "metric.type": "numeric",
                                    "metric.iteration": iteration,
                                    "metric.value": value,
                                    "config.run-flags": " ".join(params),
                                }
                            )

        return r


class PyPyJsonRule(mx_benchmark.Rule):
    """Parses a JSON file produced by the Unladen Swallow or PyPy benchmark harness and creates a measurement result."""

    def __init__(self, filename: str, suiteName: str):
        self.filename = filename
        self.suiteName = suiteName

    def parse(self, text: str) -> dict:
        r = []
        with open(self._prepend_working_dir(self.filename)) as fp:
            js = json.load(fp)

            for result in js["results"]:
                name = result[0]
                values = result[2]["base_times"]
                for iteration, value in enumerate(values):
                    r.append(
                        {
                            "bench-suite": self.suiteName,
                            "benchmark": name,
                            "metric.name": "time",
                            "metric.unit": "s",
                            "metric.score-function": "id",
                            "metric.better": "lower",
                            "metric.type": "numeric",
                            "metric.iteration": iteration,
                            "metric.value": value,
                        }
                    )

        return r


class GraalPyVm(mx_benchmark.GuestVm):
    def __init__(self, config_name, options, host_vm=None):
        super(GraalPyVm, self).__init__(host_vm=host_vm)
        self._config_name = config_name
        self._options = options

    def name(self):
        return "graalpython"

    def config_name(self):
        return self._config_name

    def hosting_registry(self):
        return mx_benchmark.java_vm_registry

    def with_host_vm(self, host_vm):
        return self.__class__(self.config_name(), self._options, host_vm)

    def run(self, cwd, args):
        ## patch host-vm name
        name = self.host_vm.name()
        name = name.replace("graalvm-ce-python", "graalvm-ce")
        name = name.replace("graalvm-ee-python", "graalvm-ee")
        type(host_vm).name = lambda s: name

        for idx,arg in enumerate(args):
            if "--vm.Xmx" in arg:
                mx.log(f"Setting Xmx from {arg}")
                break
        else:
            xmxArg = "--vm.Xmx8G"
            mx.log(f"Setting Xmx as {xmxArg}")
            args.insert(0, xmxArg)

        return self.host_vm().run_launcher("graalpy", self._options + args, cwd)


class PyPyVm(mx_benchmark.Vm):
    def config_name(self):
        return "launcher"

    def name(self):
        return "pypy"

    def interpreter(self):
        home = mx.get_env("PYPY_HOME")
        if not home:
            try:
                return (
                    subprocess.check_output("which pypy3", shell=True).decode().strip()
                )
            except OSError:
                mx.abort("{} is not set!".format("PYPY_HOME"))
        return join(home, "bin", "pypy3")

    def run(self, cwd, args):
        env = os.environ.copy()
        xmxArg = re.compile("--vm.Xmx([0-9]+)([kKgGmM])")
        pypyGcMax = "8GB"
        for idx,arg in enumerate(args):
            if m := xmxArg.search(arg):
                args = args[:idx] + args[idx + 1:]
                pypyGcMax = f"{m.group(1)}{m.group(2).upper()}B"
                mx.log(f"Setting PYPY_GC_MAX={pypyGcMax} via {arg}")
                break
        else:
            mx.log(f"Setting PYPY_GC_MAX={pypyGcMax}, use --vm.Xmx argument to override it")
        env["PYPY_GC_MAX"] = pypyGcMax
        return mx.run([self.interpreter()] + args, cwd=cwd, env=env)


class Python3Vm(mx_benchmark.Vm):
    def config_name(self):
        return "launcher"

    def name(self):
        return "cpython"

    def interpreter(self):
        home = mx.get_env("PYTHON3_HOME")
        if not home:
            return sys.executable
        if exists(exe := join(home, "bin", "python3")):
            return exe
        elif exists(exe := join(home, "python3")):
            return exe
        elif exists(exe := join(home, "python")):
            return exe
        return join(home, "bin", "python")

    def run(self, cwd, args):
        for idx,arg in enumerate(args):
            if "--vm.Xmx" in arg:
                mx.warn(f"Ignoring {arg}, cannot restrict memory on CPython.")
                args = args[:idx] + args[idx + 1:]
                break
        return mx.run([self.interpreter()] + args, cwd=cwd)


class WildcardList:
    """It is not easy to track for external suites which benchmarks are
    available, so we just return a wildcard list and assume the caller knows
    what they want to run"""

    def __contains__(self, x):
        return True

    def __iter__(self):
        mx.abort(
            "Cannot iterate over benchmark names in foreign benchmark suites. "
            + "Leave off the benchmark name part to run all, or name the benchmarks yourself."
        )


class PyPerformanceSuite(
    mx_benchmark.TemporaryWorkdirMixin, mx_benchmark.VmBenchmarkSuite
):
    VERSION = "1.0.5"

    def name(self):
        return "pyperformance-suite"

    def group(self):
        return "Graal"

    def subgroup(self):
        return "graalpython"

    def benchmarkList(self, bmSuiteArgs):
        return WildcardList()

    def rules(self, output, benchmarks, bmSuiteArgs):
        return [PyPerfJsonRule(output, self.name())]

    def createVmCommandLineArgs(self, benchmarks, runArgs):
        return []

    def get_vm_registry(self):
        return python_vm_registry

    def _vmRun(self, vm, workdir, command, benchmarks, bmSuiteArgs):
        workdir = abspath(workdir)
        vm_venv = f"{self.name()}-{vm.name()}-{vm.config_name()}"

        if not hasattr(self, "prepared"):
            self.prepared = True
            vm.run(workdir, ["-m", "venv", join(workdir, vm_venv)])
            mx.run(
                [
                    join(vm_venv, "bin", "pip"),
                    "install",
                    f"pyperformance=={self.VERSION}",
                ],
                cwd=workdir,
            )

        json_file = f"{vm_venv}.json"
        if benchmarks:
            bms = ["-b", ",".join(benchmarks)]
        else:
            bms = ["-b", ",".join(DEFAULT_PYPERFORMANCE_BENCHMARKS)]
        retcode = mx.run(
            [
                join(vm_venv, "bin", "pyperformance"),
                "run",
                "--inherit-environ",
                "PIP_INDEX_URL,PIP_TRUSTED_HOST,PIP_TIMEOUT,PIP_RETRIES,LD_LIBRARY_PATH,LIBRARY_PATH,CPATH,PATH,PYPY_GC_MAX",
                "-m",
                "-o",
                json_file,
                *bms,
            ],
            cwd=workdir,
            nonZeroIsFatal=False,
        )
        shutil.copy(join(workdir, json_file), join(SUITE.dir, "raw_results.json"))
        mx.log(f"Return code of benchmark harness: {retcode}")
        return 0, join(workdir, json_file)


class PyPySuite(mx_benchmark.TemporaryWorkdirMixin, mx_benchmark.VmBenchmarkSuite):
    VERSION = "0324a252cf1a"

    def name(self):
        return "pypy-suite"

    def group(self):
        return "Graal"

    def subgroup(self):
        return "graalpython"

    def benchmarkList(self, bmSuiteArgs):
        return WildcardList()

    def rules(self, output, benchmarks, bmSuiteArgs):
        return [PyPyJsonRule(output, self.name())]

    def createVmCommandLineArgs(self, benchmarks, runArgs):
        return []

    def get_vm_registry(self):
        return python_vm_registry

    def _vmRun(self, vm, workdir, command, benchmarks, bmSuiteArgs):
        workdir = abspath(workdir)
        vm_venv = f"{self.name()}-{vm.name()}-{vm.config_name()}"

        if not hasattr(self, "prepared"):
            self.prepared = True
            if artifact := os.environ.get("PYPY_BENCHMARKS_DIR"):
                shutil.copytree(artifact, join(workdir, "benchmarks"))
            else:
                mx.warn("PYPY_BENCHMARKS_DIR is not set, cloning repository")
                mx.run(
                    ["hg", "clone", "https://foss.heptapod.net/pypy/benchmarks"],
                    cwd=workdir,
                )
                mx.run(
                    ["hg", "up", "-C", self.VERSION], cwd=join(workdir, "benchmarks")
                )

            # workaround for pypy's benchmarks script issues
            with open(join(workdir, "benchmarks", "nullpython.py")) as f:
                content = f.read()
            content = content.replace("/usr/bin/python", "/usr/bin/env python")
            with open(join(workdir, "benchmarks", "nullpython.py"), "w") as f:
                f.write(content)

            with open(join(workdir, "benchmarks", "benchmarks.py")) as f:
                content = f.read()
            content = content.replace(
                'float(line.split(b" ")[0])', "float(line.split()[0])"
            )
            with open(join(workdir, "benchmarks", "benchmarks.py"), "w") as f:
                f.write(content)

            vm.run(workdir, ["-m", "venv", join(workdir, vm_venv)])

        json_file = f"{vm_venv}.json"
        if benchmarks:
            bms = ["-b", ",".join(benchmarks)]
        else:
            bms = ["-b", ",".join(DEFAULT_PYPY_BENCHMARKS)]
        retcode = mx.run(
            [
                sys.executable,
                join(workdir, "benchmarks", "run_local.py"),
                f"{vm_venv}/bin/python",
                "-o",
                join(workdir, json_file),
                *bms,
            ],
            cwd=workdir,
            nonZeroIsFatal=False,
        )
        shutil.copy(join(workdir, json_file), join(SUITE.dir, "raw_results.json"))
        mx.log(f"Return code of benchmark harness: {retcode}")
        return 0, join(workdir, json_file)


class NumPySuite(mx_benchmark.TemporaryWorkdirMixin, mx_benchmark.VmBenchmarkSuite):
    VERSION = "v1.16.4"
    ASV = "0.5.1"
    VIRTUALENV = "20.16.3"

    def name(self):
        return "numpy-suite"

    def group(self):
        return "Graal"

    def subgroup(self):
        return "graalpython"

    def benchmarkList(self, bmSuiteArgs):
        return WildcardList()

    def rules(self, output, benchmarks, bmSuiteArgs):
        return [AsvJsonRule(output, self.name())]

    def createVmCommandLineArgs(self, benchmarks, runArgs):
        return []

    def get_vm_registry(self):
        return python_vm_registry

    def _vmRun(self, vm, workdir, command, benchmarks, bmSuiteArgs):
        workdir = abspath(workdir)
        benchdir = join(workdir, "numpy", "benchmarks")
        vm_venv = f"{self.name()}-{vm.name()}-{vm.config_name()}"

        if not hasattr(self, "prepared"):
            self.prepared = True
            npdir = join(workdir, "numpy")
            if artifact := os.environ.get("NUMPY_BENCHMARKS_DIR"):
                shutil.copytree(artifact, npdir)
            else:
                mx.warn("NUMPY_BENCHMARKS_DIR is not set, cloning numpy repository")
                mx.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "https://github.com/numpy/numpy.git",
                        "--branch",
                        self.VERSION,
                        "--single-branch",
                    ],
                    cwd=workdir,
                )
                shutil.rmtree(join(npdir, ".git"))
            mx.run(["git", "init", "."], cwd=npdir)
            mx.run(["git", "config", "user.email", "you@example.com"], cwd=npdir)
            mx.run(["git", "config", "user.name", "YourName"], cwd=npdir)
            mx.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=npdir)
            mx.run(["git", "branch", self.VERSION], cwd=npdir)
            mx.run(["git", "branch", "main"], cwd=npdir, nonZeroIsFatal=False)
            mx.run(["git", "branch", "master"], cwd=npdir, nonZeroIsFatal=False)

            vm.run(workdir, ["-m", "venv", join(workdir, vm_venv)])
            mx.run(
                [
                    join(workdir, vm_venv, "bin", "pip"),
                    "install",
                    f"asv=={self.ASV}",
                    f"virtualenv=={self.VIRTUALENV}",
                    f"numpy=={self.VERSION}",
                ],
                cwd=workdir,
            )
            mx.run(
                [join(workdir, vm_venv, "bin", "asv"), "machine", "--yes"], cwd=benchdir
            )

        if benchmarks:
            bms = ["-b", "|".join(benchmarks)]
        else:
            bms = ["-b", "|".join(DEFAULT_NUMPY_BENCHMARKS)]
        retcode = mx.run(
            [
                join(workdir, vm_venv, "bin", "asv"),
                "run",
                "--record-samples",
                "-e",
                "--python=same",
                "--set-commit-hash",
                self.VERSION,
                *bms,
            ],
            cwd=benchdir,
            nonZeroIsFatal=False,
        )

        json_file = glob.glob(join(benchdir, "results", "*", "*numpy*.json"))
        mx.log(f"Return code of benchmark harness: {retcode}")
        if json_file:
            json_file = json_file[0]
            shutil.copy(json_file, join(SUITE.dir, "raw_results.json"))
            return 0, json_file
        else:
            return -1, ""


def register_python_benchmarks():
    global python_vm_registry, SUITE

    from mx_graalpython_benchmark import python_vm_registry as vm_registry

    python_vm_registry = vm_registry

    SUITE = mx.suite("graalpython")

    python_vm_registry.add_vm(PyPyVm())
    python_vm_registry.add_vm(Python3Vm())
    for config_name, options, priority in [
        ("launcher", [], 5),
    ]:
        python_vm_registry.add_vm(GraalPyVm(config_name, options), SUITE, priority)

    mx_benchmark.add_bm_suite(PyPerformanceSuite())
    mx_benchmark.add_bm_suite(PyPySuite())
    mx_benchmark.add_bm_suite(NumPySuite())
