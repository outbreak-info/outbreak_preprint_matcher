import subprocess
import pathlib
import os

scriptpath = pathlib.Path(__file__).parent.absolute()
update_script = os.path.join(scriptpath,'update_data.py')
compare_script = os.path.join(scriptpath,'compare_data.py')
cleanup_script = os.path.join(scriptpath,'clean_up_results.py')
program_list = [update_script,compare_script,cleanup_script]

for program in program_list:
    subprocess.call(['python', program])
    print("Finished:" + program)