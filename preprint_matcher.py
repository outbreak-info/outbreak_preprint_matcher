import subprocess
import pathlib
import os

scriptpath = pathlib.Path(__file__).parent.absolute()
retrieve_script = os.path.join(scriptpath,'fetch_known_matches.py')
update_script = os.path.join(scriptpath,'update_data.py')
compare_script = os.path.join(scriptpath,'compare_data.py')
cleanup_script = os.path.join(scriptpath,'clean_up_results.py')
program_list = [retrieve_script,update_script,compare_script,cleanup_script]

for program in program_list:
    subprocess.call(['python', program])
    print("Finished:" + program)