from sys import version_info, path
if version_info.major == 2:
    raise Exception("This script only works with python3.x!")

import os
from urllib.request import urlretrieve, build_opener, install_opener
import subprocess
from pathlib import Path
import argparse

path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.utility.SetupUtility import SetupUtility

parser = argparse.ArgumentParser()
output_dir = Path(__file__).parent / ".." / "resources" / "scenenet"
parser.add_argument('--output_folder', help="Determines where the data is going to be saved.", default=output_dir)
args = parser.parse_args()

output_dir = Path(args.output_folder)

if __name__ == "__main__":
    # setting the default header, else the server does not allow the download
    opener = build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    install_opener(opener)

    # set the download directory relative to this one
    scenenet_dir= os.path.abspath(output_dir)

    if not os.path.exists(scenenet_dir):
        os.makedirs(scenenet_dir)

    # download the zip file, which contains all the obj files
    print("Download the zip file, may take a while: ", scenenet_dir)
    scenenet_url = "https://bitbucket.org/robotvault/downloadscenenet/get/cfe5ab85ddcc.zip"
    zip_file_path = os.path.join(scenenet_dir, "scene_net.zip")
    urlretrieve(scenenet_url, zip_file_path)

    # unzip the zip file
    print("Unzip the zip file.")
    SetupUtility.extract_file(scenenet_dir, zip_file_path) 

    os.remove(zip_file_path)
    os.rename(os.path.join(scenenet_dir, "robotvault-downloadscenenet-cfe5ab85ddcc"), os.path.join(scenenet_dir, "SceneNetData"))

    print("Please also download the texture library from here: http://tinyurl.com/zpc9ppb")
    print("This is a google drive folder downloading via script is tedious.")
