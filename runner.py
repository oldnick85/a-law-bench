#!/usr/bin/env python3
"""
ALawBench orchestration script.
Builds and runs benchmarks for all combinations of:
- compilers (GCC, Clang versions)
- optimization levels (O0, O1, O2, O3)
- algorithms (tabular, naive)
"""

import argparse
import itertools
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DEFAULT_COMPILERS: Dict[str, List[str]] = {
    "gcc": ["12", "13", "14", "15"],
    "clang": ["16", "17", "18", "19", "20", "21"]
}
DEFAULT_OPT_LEVELS: List[str] = ["O0", "O1", "O2", "O3"]
DEFAULT_ALGORITHMS: List[str] = ["tabular", "naive"]

PROJECT_ROOT: Path = Path(__file__).resolve().parent
ALGORITHMS_DIR: Path = PROJECT_ROOT / "src" / "algorithms"
BENCHMARKS_DIR: Path = PROJECT_ROOT / "src" / "bench"

# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------
logger = logging.getLogger("alawbench")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ----------------------------------------------------------------------
# Dataclasses for benchmark combinations and results
# ----------------------------------------------------------------------
@dataclass
class BenchCombination:
    """A single combination of parameters to benchmark."""
    compiler: str
    version: str
    opt_level: str
    algorithm: str

@dataclass
class Throughput:
    """Samples per second measurement."""
    samples_per_second: float

@dataclass
class BenchmarkResult:
    """Complete result of one benchmark combination."""
    compiler: str
    version: str
    opt_level: str
    algorithm: str
    encode: Throughput
    decode: Throughput

# ----------------------------------------------------------------------
# Core functions
# ----------------------------------------------------------------------
def run_combination(
    combo: BenchCombination,
    temp_dir: Path,
    verbose: bool
) -> Optional[BenchmarkResult]:
    """
    Build and run a single combination inside a temporary Docker context.

    Returns a BenchmarkResult on success, None on failure.
    """
    image_tag = f"a-law-bench-{combo.compiler}{combo.version}-{combo.opt_level}-{combo.algorithm}".lower()
    container_name = f"{image_tag}-run"

    # Create temporary build context
    context_dir = temp_dir / image_tag
    context_dir.mkdir(parents=True, exist_ok=True)

    # Copy sources
    dest_algorithms = context_dir / "src" / "algorithms"
    dest_benchmarks = context_dir / "src" / "bench"
    shutil.copytree(ALGORITHMS_DIR, dest_algorithms, dirs_exist_ok=True)
    shutil.copytree(BENCHMARKS_DIR, dest_benchmarks, dirs_exist_ok=True)
    shutil.copy(PROJECT_ROOT / "CMakeLists.txt", context_dir / "CMakeLists.txt")

    # Base image and compiler executable name
    if combo.compiler == "gcc":
        base_image = f"gcc:{combo.version}"
        compiler_exec = "g++"
    else:
        base_image = f"silkeh/clang:{combo.version}"
        compiler_exec = f"clang++-{combo.version}"

    # Dockerfile
    dockerfile_content = f"""FROM {base_image}

# Install cmake (if not present)
RUN apt-get update && apt-get install -y cmake && rm -rf /var/lib/apt/lists/*

# Copy sources
WORKDIR /source
COPY src /source/src
COPY CMakeLists.txt /source/

# Build
WORKDIR /build
RUN cmake /source \
        -DCMAKE_CXX_COMPILER={compiler_exec} \
        -DCMAKE_CXX_FLAGS="-{combo.opt_level}" \
        -DALGORITHM_DIR={combo.algorithm} \
        -DALGORITHM_NAME={combo.algorithm}
RUN cmake --build .

# Run benchmark
CMD ["./bench"]
"""
    dockerfile_path = context_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content)

    # Build image
    logger.info(f"--- Building {image_tag} ---")
    build_cmd = ["docker", "build", "-t", image_tag, str(context_dir)]
    build_result = subprocess.run(build_cmd, capture_output=True, text=True)
    if verbose:
        if build_result.stdout:
            logger.debug(f"Build stdout: {build_result.stdout}")
        if build_result.stderr:
            logger.debug(f"Build stderr: {build_result.stderr}")
    if build_result.returncode != 0:
        logger.error(f"Build failed: {build_result.stderr}")
        return None

    # Run container
    logger.info(f"--- Running {image_tag} ---")
    run_cmd = ["docker", "run", "--name", container_name, image_tag]
    run_result = subprocess.run(run_cmd, capture_output=True, text=True)
    if verbose:
        if run_result.stdout:
            logger.debug(f"Run stdout: {run_result.stdout}")
        if run_result.stderr:
            logger.debug(f"Run stderr: {run_result.stderr}")

    # Always remove container and image
    subprocess.run(["docker", "rm", container_name], capture_output=True)
    subprocess.run(["docker", "rmi", image_tag], capture_output=True)

    if run_result.returncode != 0:
        logger.error(f"Run failed: {run_result.stderr}")
        output = run_result.stdout  # try to parse anyway
    else:
        output = run_result.stdout

    # Parse JSON output (expecting last line to be JSON)
    try:
        data = json.loads(output.strip().split('\n')[-1])
        # Convert to dataclass
        result = BenchmarkResult(
            compiler=combo.compiler,
            version=combo.version,
            opt_level=combo.opt_level,
            algorithm=combo.algorithm,
            encode=Throughput(samples_per_second=data["encode"]["samples_per_second"]),
            decode=Throughput(samples_per_second=data["decode"]["samples_per_second"])
        )
        return result
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error(f"Failed to parse JSON output: {e}")
        logger.error(f"Output was: {output}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run A-law benchmarks across compilers and optimizations.")
    parser.add_argument("--compilers", nargs="+", choices=["gcc", "clang"], default=["gcc", "clang"],
                        help="Compilers to test")
    parser.add_argument("--gcc-versions", nargs="+", default=DEFAULT_COMPILERS["gcc"],
                        help="GCC versions")
    parser.add_argument("--clang-versions", nargs="+", default=DEFAULT_COMPILERS["clang"],
                        help="Clang versions")
    parser.add_argument("--opt-levels", nargs="+", default=DEFAULT_OPT_LEVELS,
                        help="Optimization levels")
    parser.add_argument("--algorithms", nargs="+", default=DEFAULT_ALGORITHMS,
                        help="Algorithm implementations")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print build and run output (sets logging to DEBUG)")
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Build combination list using dataclass
    combos: List[BenchCombination] = []
    for compiler in args.compilers:
        versions = args.gcc_versions if compiler == "gcc" else args.clang_versions
        for version, opt, algo in itertools.product(versions, args.opt_levels, args.algorithms):
            combos.append(BenchCombination(compiler, version, opt, algo))

    logger.info(f"Total combinations: {len(combos)}")

    results: List[BenchmarkResult] = []
    with tempfile.TemporaryDirectory(prefix="a-law-bench-") as tmpdir:
        temp_dir = Path(tmpdir)
        for combo in combos:
            res = run_combination(combo, temp_dir, args.verbose)
            if res:
                results.append(res)

    if not results:
        logger.error("No results obtained.")
        return

    # Print markdown summary
    print("\n## Summary (samples per second, higher is better)")
    print("| Compiler | Version | Opt | Algorithm | Encode (samples/s) | Decode (samples/s) |")
    print("|----------|---------|-----|-----------|--------------------|--------------------|")
    for r in results:
        print(f"| {r.compiler} | {r.version} | {r.opt_level} | {r.algorithm} | "
              f"{r.encode.samples_per_second:.2e} | {r.decode.samples_per_second:.2e} |")


if __name__ == "__main__":
    main()