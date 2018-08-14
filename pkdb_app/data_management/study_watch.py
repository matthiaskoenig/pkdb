#!/usr/bin/python
import time
import argparse
import os, sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from pkdb_app.data_management.study_upload import run as upload_study



class MyHandler(FileSystemEventHandler):
    def __init__(self,  study):
        self.study = study

    def on_created(self, event):
        #if  event.is_directory:
        _, study_name = os.path.split(self.study)

        print(f'---------- Study: {study_name} ----------')
        upload_study(self)


def run(args):
    event_handler = MyHandler(study = args.study)
    observer = Observer()
    observer.schedule(event_handler, path=args.study, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a file to PKDB")
    parser.add_argument("-s", help="directory of a study", dest="study", type=str, required=True)
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


