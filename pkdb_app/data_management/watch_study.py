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
import coloredlogs
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

coloredlogs.install(
    level='INFO',
    fmt="%(module)s:%(lineno)s %(funcName)s %(levelname) -10s %(message)s"
    # fmt="%(levelname) -10s %(asctime)s %(module)s:%(lineno)s %(funcName)s %(message)s"
)
logger = logging.getLogger(__name__)


BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import upload_study_from_dir

# FIXME: make sure that removed files are removed from the study (on delete?)


class StudyHandler(FileSystemEventHandler):
    """ Handler for study folder. """
    def __init__(self, path):

        self.path = path
        _, study_name = os.path.split(self.path)
        self.study_name = study_name
        logging.info('-' * 80)
        logging.info(f'Watching [{self.study_name}]')
        logging.info(f'\t{self.path}')
        logging.info('-' * 80)
        upload_study_from_dir(self.path)

    def on_modified(self, event):
        """ Executed on modified event.
        :param event:
        :return:
        """
        logging.info('\n')
        logging.info('-' * 80)
        logging.info(f'Updating [{self.study_name}]')
        logging.info('-' * 80)
        upload_study_from_dir(self.path)


def start_observer(args):
    """ Run observer. """

    # normalize path
    path = os.path.abspath(args.path)
    if path.endswith("/"):
         path = path[:-1]
    if not os.path.exists(path) or not os.path.isdir(path):
        print(path)
        raise FileNotFoundError

    # start event handling
    event_handler = StudyHandler(path=path)
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Watch a study directory for changes")
    parser.add_argument("-s", help="path to study directory", dest="path", type=str, required=True)
    parser.set_defaults(func=start_observer)
    args = parser.parse_args()
    args.func(args)
