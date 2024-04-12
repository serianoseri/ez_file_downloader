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
import uuid
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

def copy_url(task_id: TaskID, url: str, path: str, progress: Progress, cookie: dict) -> None:
    """Copy data from a url to a local file."""
    #progress.console.log(f"Requesting {url}")
    global i
    #cookie = dict(MoodleSession='k3h38ved4o4g4nodg42hdn9p4j')
    filename = path.split("/")[-1]
    response = requests.get(url, stream = True, cookies=cookie)
    filesize = int(response.headers.get('Content-Length', 0))
    if filesize == 0:
        filesize = int(len(response.content))
    #cprint('Filesize: ' + str(filesize) + " bytes", "yellow")
    progress.update(task_id, total=filesize)
    if response.status_code == 200 and filesize > 0:
        with open(path, "wb") as dest_file:
            progress.start_task(task_id)
            for data in response.iter_content(chunk_size=1024*1024):
                if data:
                    dest_file.write(data)
                    progress.update(task_id, advance=len(data))
                #if progress.finished:
                    #return
    elif filesize == 0:
        cprint(filename + ": Cannot download file of size 0", "red")
        progress.remove_task(task_id)
    else:
        cprint("Status code : " + str(response.status_code), "red")
        progress.remove_task(task_id)

def download(url: str, dest_dir: str, filename: str, cookie: dict):
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
        #filename = url.split("/")[-1]
        dest_path = os.path.join(dest_dir, filename)
        task_id = progress.add_task("Downloading", filename=filename, start=False, visible=True)
        copy_url(task_id, url, dest_path, progress, cookie)
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
argParser.add_argument('-l', '--link', help = 'txt file with downloadable links in it', type = check_in_path, required = True)
argParser.add_argument('-d', '--outdir', help = 'path of the output direcotry, if not specified the default is dir downloads', type=str, default='downloads', required=False)
argParser.add_argument('-cl', '--clean', help='remove the GET parameters from the link', action='store_true')
argParser.add_argument('-c', '--cookies', help = 'path/to/txt/file that contains cookies, N lines = N cookies, with the format cookie=\'value\'')

args = argParser.parse_args()

def prevent_duplicate(folder,filename):
    i = 1
    limit = 0
    duplicate_indicator = f'({i})'
    #if file doesn't exist return the filename
    path_to_file = os.path.join(folder, filename)
    while os.path.exists(path_to_file) and limit < 10:
        if duplicate_indicator in filename:
            #cprint('BINGO', 'red')
            filename = filename.replace(f'({i})', f'({i+1})')
            duplicate_indicator = f'({i+1})'
        else:
            filename = filename.rsplit('.', 1)
            filename = filename[0] + '(' + str(i) + ').' + filename[1]
        i += 1
        limit += 1
        path_to_file = os.path.join(folder, filename)
    #cprint('File already exists, renaming to: ' + filename, 'yellow')
    return filename

dir_downloads = args.outdir
if args.outdir == "":
    dir_downloads = "downloads"
ensure_dir(dir_downloads)

links = open(args.link, 'r')
current = ''
ffmpeg_hls_stream = 'ffmpeg -f hls -f hls -i "|link|" -c copy -bsf:a aac_adtstoasc |pathname|.mp4'
hls = ''
hls_name = ''
isfolder = False

cookie = {}
cprint(cookie)
#setting cookies if present
if args.cookies != "":
    with open(args.cookies, "r") as cookie_file:
        lines = cookie_file.readlines()

        for line in lines:
            key, value = line.strip().split(',')
            cookie[key] = value

for link in links:
    link = link.strip()
    if args.clean:
        link = link.rsplit('?', 1)[0]
    name = requests.utils.unquote(link.rsplit('/', 1)[-1])
    extension = link.rsplit('.', 1)[-1]
    filename = os.path.join(current, name)

    if(os.path.isfile(path=filename) and not link.startswith('/folder/')):
        filename = os.path.join(current, prevent_duplicate(current,name))
        #cprint('File: ' + filename, 'green')
        #dirty fix to always get a unique filename using uuid4()
        #filename = os.path.join(current, 'renamed_' + str(uuid.uuid4()) + '.' +  extension)

    if link.startswith('/folder/'):
        newpath = dir_downloads + slash + link.replace('/folder/', '')
        current = newpath
        ensure_dir(newpath)
        isfolder = True
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
    elif not os.path.isfile(filename) and current != '' and not link.startswith('/hls/') and not isfolder:
        download(link, current, filename.split(slash)[-1], cookie)
    else: 
        cprint("skipped link: " + link, "yellow")

    isfolder = False
