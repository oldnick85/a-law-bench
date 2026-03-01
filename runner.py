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
import shutil
import subprocess
import tempfile
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DEFAULT_COMPILERS = {
    "gcc": ["12", "13", "14", "15"],
    "clang": ["16", "17", "18", "19", "20", "21"]
}
DEFAULT_OPT_LEVELS = ["O0", "O1", "O2", "O3"]
DEFAULT_ALGORITHMS = ["tabular", "naive"]

# Paths inside container (must match project structure)
PROJECT_ROOT = Path(__file__).resolve().parent
ALGORITHMS_DIR = PROJECT_ROOT / "src" / "algorithms"
BENCHMARKS_DIR = PROJECT_ROOT / "src" / "bench"

def run_combination(compiler, version, opt_level, algorithm, temp_dir):
    """
    Build and run a single combination inside a temporary Docker context.
    Returns a dict with results or None on failure.
    """
    image_tag = f"a-law-bench-{compiler}{version}-{opt_level}-{algorithm}".lower()
    container_name = f"{image_tag}-run"

    # Create a temporary directory with Dockerfile and all sources
    context_dir = temp_dir / image_tag
    context_dir.mkdir(parents=True, exist_ok=True)

    # Copy entire project to context
    dest_algorithms = context_dir / "src" / "algorithms"
    dest_benchmarks = context_dir / "src" / "bench"
    shutil.copytree(ALGORITHMS_DIR, dest_algorithms, dirs_exist_ok=True)
    shutil.copytree(BENCHMARKS_DIR, dest_benchmarks, dirs_exist_ok=True)
    shutil.copy(PROJECT_ROOT / "CMakeLists.txt", context_dir / "CMakeLists.txt")

    # Base image and compiler executable name
    if compiler == "gcc":
        base_image = f"gcc:{version}"
        compiler_exec = "g++"
    else:
        base_image = f"silkeh/clang:{version}"
        compiler_exec = f"clang++-{version}"

    # Generate Dockerfile
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
        -DCMAKE_CXX_FLAGS="-{opt_level}" \
        -DALGORITHM_DIR={algorithm} \
        -DALGORITHM_NAME={algorithm}
RUN cmake --build .

# Run benchmark
CMD ["./bench"]
"""
    dockerfile_path = context_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content)

    # Build image
    print(f"\n--- Building {image_tag} ---")
    build_cmd = ["docker", "build", "-t", image_tag, str(context_dir)]
    try:
        subprocess.run(build_cmd)
        #subprocess.run(build_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e.stderr}")
        return None

    # Run container and capture output
    print(f"--- Running {image_tag} ---")
    run_cmd = ["docker", "run", "--name", container_name, image_tag]
    try:
        result = subprocess.run(run_cmd, check=True, capture_output=True, text=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Run failed: {e.stderr}")
        output = e.stdout  # maybe partial JSON?
    finally:
        # Remove container
        subprocess.run(["docker", "rm", container_name], capture_output=True)

    # Remove image (cleanup)
    subprocess.run(["docker", "rmi", image_tag], capture_output=True)

    # Parse JSON output
    try:
        # The benchmark prints a single JSON line
        data = json.loads(output.strip().split('\n')[-1])
        # Add metadata
        data["compiler"] = compiler
        data["version"] = version
        data["opt_level"] = opt_level
        return data
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Failed to parse JSON output: {e}")
        print(f"Output was: {output}")
        return None

def main():
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
    args = parser.parse_args()

    # Prepare list of combinations
    combos = []
    for compiler in args.compilers:
        versions = args.gcc_versions if compiler == "gcc" else args.clang_versions
        for version, opt, algo in itertools.product(versions, args.opt_levels, args.algorithms):
            combos.append((compiler, version, opt, algo))

    print(f"Total combinations: {len(combos)}")

    results = []
    with tempfile.TemporaryDirectory(prefix="a-law-bench-") as tmpdir:
        temp_dir = Path(tmpdir)
        for compiler, version, opt, algo in combos:
            res = run_combination(compiler, version, opt, algo, temp_dir)
            if res:
                results.append(res)

    if not results:
        print("No results obtained.")
        return

    # Print a simple markdown table
    print("\n## Summary (samples per second, higher is better)")
    print("| Compiler | Version | Opt | Algorithm | Encode (samples/s) | Decode (samples/s) |")
    print("|----------|---------|-----|-----------|--------------------|--------------------|")
    for r in results:
        print(f"| {r['compiler']} | {r['version']} | {r['opt_level']} | {r['algorithm']} | "
              f"{r['encode']['samples_per_second']:.2e} | {r['decode']['samples_per_second']:.2e} |")

if __name__ == "__main__":
    main()