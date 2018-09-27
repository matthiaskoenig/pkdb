"""
Watchdog to observe study folder for changes.
Updates study on changes.

(pkdb) python ~/git/pkdb/pkdb_app/data_management/watch_study.py -s PATH_TO_DIRECTORY

"""
import os
import time
import argparse
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from pkdb_app import logging_utils
from pkdb_app.data_management.fill_database import upload_study_from_dir
from pkdb_app.data_management.setup_database import get_authentication_headers

logger = logging.getLogger(__name__)


class StudyHandler(FileSystemEventHandler):
    """ Handler for study folder. """

    def __init__(self, path):

        self.path = path
        _, study_name = os.path.split(self.path)
        self.study_name = study_name
        logging.info("-" * 80)
        logging.info(f"Watching [{self.study_name}]")
        logging.info(f"\t{self.path}")
        logging.info("-" * 80)
        self.HEADER = get_authentication_headers()
        upload_study_from_dir(self.path,self.HEADER)

    def on_modified(self, event):
        """ Executed on modified event.
        :param event:
        :return:
        """
        logging.info("\n")
        logging.info("-" * 80)
        logging.info(f"Updating [{self.study_name}]")
        logging.info("-" * 80)
        upload_study_from_dir(self.path,self.HEADER)


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
    parser.add_argument(
        "-s", help="path to study directory", dest="path", type=str, required=True
    )
    parser.set_defaults(func=start_observer)
    args = parser.parse_args()
    args.func(args)
