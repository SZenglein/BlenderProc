import subprocess
import os
import argparse
import random

parser = argparse.ArgumentParser("Rerun script for BlenderProc")
parser.add_argument("--seed",  help="Seed used for the generation")
parser.add_argument("params", help="The params which are handed over to the run.py script", nargs='+')
args = parser.parse_args()

seed = random.randint(0, 1000000)
env = os.environ
if args.seed:
    seed = args.seed

print("running rerun.py with seed", seed)
random.seed(seed)

# this sets the amount of runs, which are performed
amount_of_runs = 100

# set the folder in which the run.py is located
rerun_folder = os.path.abspath(os.path.dirname(__file__))

# the first one is the rerun.py script, the last is the output
used_arguments = list(args.params)
output_location = os.path.abspath(used_arguments[-1])
for run_id in range(amount_of_runs):
    run_seed = random.randint(0, 1000000)
    # in each run, the arguments are reused
    cmd = ["python", os.path.join(rerun_folder, "run.py")]
    cmd.extend(used_arguments)
    # the only exception is the output, which gets changed for each run, so that the examples are not overwritten
    cmd.append(os.path.join(output_location, str(seed), str(run_seed)))
    if seed:
        env["BLENDER_PROC_RANDOM_SEED"] = str(run_seed)
    print(" ".join(cmd))
    # execute one BlenderProc run
    subprocess.call(" ".join(cmd), shell=True, env=env)