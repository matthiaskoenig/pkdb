#!/usr/bin/python
"""
Watchdog to observe study folder for changes.
Updates study on changes.

(pkdb) python ~/git/pkdb/pkdb_app/data_management/watch_study.py -s PATH_TO_DIRECTORY

"""

import os
import sys
import time
import argparse
import logging

logging.getLogger().setLevel(logging.INFO)

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import upload_study_from_dir

# FIXME: make sure that removed files are removed from the study (on delete?)


class StudyHandler(FileSystemEventHandler):
    def __init__(self,  study):
        self.study = study
        _, study_name = os.path.split(self.study)
        logging.info('-' * 80)
        logging.info(f'Watching [{study_name}]')
        logging.info(f'\t{self.study}')
        logging.info('-' * 80)
        upload_study_from_dir(self.study)

    def on_created(self, event):
        print('\n')
        upload_study_from_dir(self.study)


def run(args):
    """ Run observer. """
    event_handler = StudyHandler(study=args.study)
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
    parser = argparse.ArgumentParser(description="Watch a study folder for changes")
    parser.add_argument("-s", help="directory of study", dest="study", type=str, required=True)
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)