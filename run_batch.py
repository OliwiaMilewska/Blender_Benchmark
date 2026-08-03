#!/usr/bin/env python3
"""
Run multiple benchmark configs sequentially.

Examples:
  python run_batch.py config/C1.yaml config/C3.yaml config/C4.yaml
  python run_batch.py --manifest config/batch_example.yaml
  python run_batch.py --glob "config/C1.yaml" --glob "config/E1.yaml"
  python run_batch.py --manifest config/batch_example.yaml --dry-run
"""
import argparse
import os
import sys
import time
from pathlib import Path

import yaml
from tqdm.auto import tqdm

sys.path.insert(0, os.path.dirname(__file__))

from src.blender_benchmark.cli import run_config_file


def load_manifest(manifest_path):
    """Load config paths and batch options from a YAML manifest."""
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    configs = data.get("configs", [])
    if not configs:
        raise ValueError(f"Manifest has no configs: {manifest_path}")

    return {
        "configs": [str(item) for item in configs],
        "wait_between_configs": data.get("wait_between_configs", 0),
        "stop_on_error": data.get("stop_on_error", True),
        "repeat": data.get("repeat"),
        "wait": data.get("wait"),
    }


def resolve_config_paths(configs, globs, manifest):
    """Build an ordered, de-duplicated list of config file paths."""
    paths = []

    if manifest:
        manifest_data = load_manifest(manifest)
        paths.extend(manifest_data["configs"])
    paths.extend(configs or [])

    for pattern in globs or []:
        paths.extend(str(p) for p in sorted(Path().glob(pattern)))

    unique_paths = []
    seen = set()
    for path in paths:
        normalized = str(Path(path))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_paths.append(normalized)

    return unique_paths


def validate_config_paths(config_paths):
    """Return existing paths and report missing files."""
    valid = []
    missing = []

    for path in config_paths:
        if Path(path).exists():
            valid.append(path)
        else:
            missing.append(path)

    return valid, missing


def run_batch(
    config_paths,
    wait_between_configs=0,
    stop_on_error=True,
    repeat_override=None,
    wait_override=None,
    dry_run=False,
):
    """Run configs one after another."""
    valid_paths, missing_paths = validate_config_paths(config_paths)

    if missing_paths:
        for path in missing_paths:
            print(f"❌ Config not found: {path}")
        if not valid_paths:
            return 1

    total = len(valid_paths)
    print(f"\nBatch benchmark: {total} config(s) queued\n")

    if dry_run:
        for index, path in enumerate(valid_paths, start=1):
            print(f"  {index}. {path}")
        print("\nDry run complete — nothing executed.")
        return 0

    failed = []
    completed = 0
    for index, config_path in enumerate(valid_paths, start=1):
        print("\n" + "#" * 70)
        print(f"BATCH {index}/{total}: {config_path}")
        print("#" * 70 + "\n")

        success = run_config_file(
            config_path,
            repeat_override=repeat_override,
            wait_override=wait_override,
        )

        if not success:
            failed.append(config_path)
            print(f"\n❌ Failed: {config_path}")
            if stop_on_error:
                print("Stopping batch because stop_on_error=true")
                break
        else:
            completed += 1
            print(f"\n✓ Completed: {config_path}")

        if index < total and wait_between_configs > 0:
            print(
                f"\n⏳ Waiting {wait_between_configs}s before next config..."
            )
            for _ in tqdm(
                range(wait_between_configs),
                desc="Between configs",
                unit="s",
                leave=False,
            ):
                time.sleep(1)

    print("\n" + "=" * 70)
    print("BATCH SUMMARY")
    print("=" * 70)
    print(f"Total queued: {total}")
    print(f"Completed: {completed}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed configs:")
        for path in failed:
            print(f"  - {path}")
        return 1

    print("\n✓ All configs completed successfully.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Run multiple Blender benchmark configs sequentially",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_batch.py config/C1.yaml config/C3.yaml
  python run_batch.py --manifest config/batch_example.yaml
  python run_batch.py --glob "config/C1.yaml" --glob "config/C3.yaml"
  python run_batch.py --manifest config/batch_example.yaml --continue-on-error
        """,
    )

    parser.add_argument(
        "configs",
        nargs="*",
        help="Paths to YAML config files",
    )
    parser.add_argument(
        "--manifest",
        help="YAML file listing configs to run (field: configs)",
    )
    parser.add_argument(
        "--glob",
        action="append",
        dest="globs",
        help="Add configs matching a glob pattern (can be repeated)",
    )
    parser.add_argument(
        "--wait-between",
        type=int,
        default=None,
        help="Seconds to wait between configs (overrides manifest value)",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=None,
        help="Override repeat count for every config in the batch",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=None,
        help="Override wait between iterations for every config in the batch",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        default=None,
        help="Stop batch when a config fails (default)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with remaining configs after a failure",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print queued configs without running benchmarks",
    )

    args = parser.parse_args()

    manifest_data = {}
    if args.manifest:
        try:
            manifest_data = load_manifest(args.manifest)
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ {e}")
            return 1

    config_paths = resolve_config_paths(args.configs, args.globs, args.manifest)
    if not config_paths:
        print("❌ No configs specified.")
        print("Provide config paths, --manifest, or --glob.")
        return 1

    wait_between = args.wait_between
    if wait_between is None:
        wait_between = manifest_data.get("wait_between_configs", 0)

    if args.continue_on_error:
        stop_on_error = False
    elif args.stop_on_error is not None:
        stop_on_error = True
    else:
        stop_on_error = manifest_data.get("stop_on_error", True)

    repeat_override = args.repeat
    if repeat_override is None:
        repeat_override = manifest_data.get("repeat")

    wait_override = args.wait
    if wait_override is None:
        wait_override = manifest_data.get("wait")

    return run_batch(
        config_paths=config_paths,
        wait_between_configs=wait_between,
        stop_on_error=stop_on_error,
        repeat_override=repeat_override,
        wait_override=wait_override,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
