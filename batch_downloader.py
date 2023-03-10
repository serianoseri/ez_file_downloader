#!/usr/bin/python3.3
import os.path
from os.path import exists
import requests
import re
import argparse
import sys
from termcolor import colored, cprint
import functools
import shutil
import signal
from threading import Event

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

done_event = Event()

def handle_sigint(signum, frame):
    done_event.set()

signal.signal(signal.SIGINT, handle_sigint)

def copy_url(task_id: TaskID, url: str, path: str, progress: Progress) -> None:
    """Copy data from a url to a local file."""
    #progress.console.log(f"Requesting {url}")
    global i
    response = requests.get(url, stream = True)
    filesize = int(response.headers.get('Content-Length', 0))
    # This will break if the response doesn't contain content length
    progress.update(task_id, total=filesize)
    with open(path, "wb") as dest_file:
        progress.start_task(task_id)
        for data in response.iter_content(chunk_size=32*1024):
            if data:
                dest_file.write(data)
                progress.update(task_id, advance=len(data))
            if progress.finished:
                return

def download(url: str, dest_dir: str):
    """Download file to the given directory."""
    progress = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        refresh_per_second=30,
        auto_refresh=True,
    )
    with progress:
        filename = url.split("/")[-1]
        dest_path = os.path.join(dest_dir, filename)
        task_id = progress.add_task("Downloading", filename=filename, start=False, visible=True)
        copy_url(task_id, url, dest_path, progress)
        #progress.remove_task(task_id)
        return

#create path if doesn't exist
def ensure_dir(path):
    #directory = os.path.dirname(file_path)
    if not os.path.exists(path):
        os.makedirs(path)
#check if path is valid, if not print error and command help
def check_in_path(path):
    if exists(path):
        return path
    else:
        cprint('Invalid argument, not of type path or invalid path', 'red', file=sys.stderr)
        argParser.print_help(sys.stderr)
        sys.exit(2)

'''
checking the os for selecting the path separator 
    \ on windows
    / on linux/macOS
    if the user is on a different OS it will stop the execution of the script telling the user that is on an unsupported os
'''
slash = ''
if sys.platform == 'win32':
    slash = '\\'
elif sys.platform == 'linux' or sys.platform == 'darwin':
    slash = '/'
else:
    cprint('[ERROR] you are on an unsupported operating system', 'red', file=sys.stderr)
    sys.exit(1)

argParser = argparse.ArgumentParser()
argParser.add_argument("-l", "--link", help = "txt file with downloadable links in it", type = check_in_path, required = True)
argParser.add_argument('-d', '--outdir', help = 'path of the output direcotry, if not specified the default is dir downloads', type=str, default='downloads', required=False)
argParser.add_argument('-c', '--clean', help='remove the GET parameters from the link', action='store_true')

args = argParser.parse_args()

dir_downloads = args.outdir
ensure_dir(dir_downloads)
links = open(args.link, 'r')
current = ''
ffmpeg_hls_stream = 'ffmpeg -f hls -f hls -i "|link|" -c copy -bsf:a aac_adtstoasc |pathname|.mp4'
hls = ''
hls_name = ''

for link in links:
    link = link.strip()
    if args.clean:
        link = link.rsplit('?', 1)[0]
    name = link.rsplit('/', 1)[-1]
    filename = os.path.join(current, name)

    if link.startswith('/folder/'):
        newpath = dir_downloads + slash + link.replace('/folder/', '')
        current = newpath
        ensure_dir(newpath)
    elif link.startswith('/hls_name/'):
        hls_name = link.replace('/hls_name/', '')
    elif link.startswith('/hls/') and not os.path.isfile(current + slash + hls_name + '.mp4'):
        hls = link.replace('/hls/', '', 1)
        print("hls-name: " + hls_name)
        print("hls-link: " + hls)
        command_to_use = ffmpeg_hls_stream.replace('|link|', hls)
        command_to_use = command_to_use.replace('|pathname|', current + slash + hls_name)
        
        os.system(f'cmd /c "{command_to_use}"')
        hls = ''
    elif link == '':
        current = ''
    elif not os.path.isfile(filename) and current != '' and not link.startswith('/hls/'):
            download(link, current)