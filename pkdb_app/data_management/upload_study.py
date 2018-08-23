#! /usr/bin/env python
"""
Script which allows to upload single study from folder.
Is used in watchdog.
"""
import os
import sys
import argparse
import coloredlogs, logging

logger = logging.getLogger(__name__)
coloredlogs.install(level='INFO')

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import upload_study_from_dir


def run(args):
    upload_study_from_dir(args.study)


def main():
    parser = argparse.ArgumentParser(description="Upload a study to PKDB")
    parser.add_argument("-s", help="directory of study", dest="study", type=str, required=True)
    parser.add_argument("--r", help="create reference json", action="store_true")

    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
