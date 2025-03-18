import os
import argparse
import time
from datetime import datetime
from pathlib import Path
import random
import logging
import asyncio
import subprocess

async def increment_version_after(delay: int, version_file: Path):
    """ Increments a file with a single integer by one, and runs git commit/push. """
    # wait time in seconds
    await asyncio.sleep(delay)
    
    # read new version
    with version_file.open() as f:
        version = int(f.read().strip())
    logging.info(f"updating {version_file} from {version} to {version+1}.")
    
    version += 1
    # write new version
    with version_file.open('w') as f:
        print(version, file=f)

    # git commit and push
    cwd = str(version_file.parent)
    subprocess.run(["git", "commit", "-a", "-m", f'"Updating version to {version}."'], cwd=cwd)
    subprocess.run(["git", "push"], cwd=cwd)
    logging.info(f"commited {version_file} at {delay} and pushed repo.")

def _debug_transform_to_workday_seconds(value: float) -> int:
    return round(value)

def _transform_to_workday_seconds(value: float) -> int:
    """ Transforms a [0.,1.] value to workday seconds. """
    # start at 8:30
    start_day = 8.5 * 60 * 60
    # finish working 9 hrs later.
    return round(start_day + value * 9 * 60 * 60)

async def schedule_updates(path: Path, path_index: int, lambd: float):
    """ Creates a schedule of delayed updates with a max of 5 updates a day. """
    pid = os.getpid()
    seed = pid + path_index
    r = random.Random(seed)

    freq = min(5,round(r.expovariate(lambd)))

    delays = [_transform_to_workday_seconds(r.random()) for _ in range(freq)]

    logging.info(f"{1./lambd:.3f} generated {freq} updates for {path} at {delays} times with seed {seed}.")

    tasks = [increment_version_after(d, path / "VERSION") for d in delays]
    for t in tasks:
        await t

async def main(args):    
    mean = args.mean * args.weekend_discount if datetime.now().weekday() >= 5 else args.mean

    lambd = 1. / mean
    tasks = [asyncio.create_task(schedule_updates(Path(p), i, lambd)) for i, p in enumerate(args.paths)]
    
    for t in tasks:
        await t

    logging.info("finished.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="updates VERSION on repos by increment 1.")
    parser.add_argument("paths", nargs='+', help="path of repositories")
    parser.add_argument("--weekend-discount", dest='weekend_discount', type=float, default=0.1, help="discount to frequency for weekend.")
    parser.add_argument("--mean", dest='mean', type=float, default=0.66, help="mean frequency of updates per day.")

    args = parser.parse_args()
    logging.basicConfig(filename="/tmp/simulation_update.log", filemode='a', level=logging.INFO, format="%(asctime)s:%(process)d:%(levelname)s:%(message)s")

    asyncio.run(main(args))
