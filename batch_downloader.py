#!/usr/bin/python3.3
import os.path
from os.path import exists
import requests
#from clint.textui import progress
import re
import argparse
import sys
from termcolor import colored, cprint
#from tqdm.auto import tqdm
import functools
import shutil

from concurrent.futures import ThreadPoolExecutor
import signal
from functools import partial
from threading import Event
from typing import Iterable

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

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


done_event = Event()


def handle_sigint(signum, frame):
    done_event.set()

signal.signal(signal.SIGINT, handle_sigint)

def copy_url(task_id: TaskID, url: str, path: str) -> None:
    """Copy data from a url to a local file."""
    #progress.console.log(f"Requesting {url}")
    global i
    response = requests.get(url, stream = True)
    # This will break if the response doesn't contain content length
    progress.update(task_id, total=int(response.headers.get('Content-Length', 0)))
    with open(path, "wb") as dest_file:
        progress.start_task(task_id)
        for data in response.iter_content(chunk_size=32*1024):
            if data:
                dest_file.write(data)
                progress.update(task_id, advance=len(data))
            if progress.finished:
                return
    #progress.console.log(f"Downloaded {path}\n")

def download(url: str, dest_dir: str):
    """Download file to the given directory."""
    with progress:
        filename = url.split("/")[-1]
        dest_path = os.path.join(dest_dir, filename)
        task_id = progress.add_task("Downloading", filename=filename, start=False, visible=True)
        copy_url(task_id, url, dest_path)
        progress.refresh()
        task_id = ''
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

argParser = argparse.ArgumentParser()
argParser.add_argument("-l", "--link", help = "txt file with downloadable links in it", type = check_in_path, required = True)

args = argParser.parse_args()

dir_downloads = 'downloads'
ensure_dir(dir_downloads)
links = open(args.link, 'r')
current = ''
ffmpeg_hls_stream = 'ffmpeg -f hls -f hls -i "|link|" -c copy -bsf:a aac_adtstoasc |pathname|.mp4'
hls = ''
hls_name = ''

for link in links:
    link = link.strip()
    name = link.rsplit('/', 1)[-1]
    filename = os.path.join(current, name)
    
    if link.startswith('/folder/'):
        newpath = dir_downloads + '\\' + link.replace('/folder/', '')
        current = newpath
        ensure_dir(newpath)
    elif link.startswith('/hls_name/'):
        hls_name = link.replace('/hls_name/', '')
    elif link.startswith('/hls/') and not os.path.isfile(current + '\\' + hls_name + '.mp4'):
        hls = link.replace('/hls/', '', 1)
        print("hls-name: " + hls_name)
        print("hls-link: " + hls)
        command_to_use = ffmpeg_hls_stream.replace('|link|', hls)
        command_to_use = command_to_use.replace('|pathname|', current + '\\' + hls_name)
        
        os.system(f'cmd /c "{command_to_use}"')
        hls = ''
    elif link == '':
        current = ''
    elif not os.path.isfile(filename) and current != '' and not link.startswith('/hls/'):
            download(link, current)
