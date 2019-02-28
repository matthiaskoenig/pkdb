"""
Script which allows to upload single study from folder.
Is used in watchdog.
"""

import argparse
import logging
from pkdb_app.data_management.upload_studies import upload_study_from_dir
from pkdb_app.data_management.setup_database import get_authentication_headers
from pkdb_app.settings import API_URL

logger = logging.getLogger(__name__)


def run(args):
    study_dir = args.study
    logger.info(f"study_dir: {study_dir}")

    upload_study_from_dir(study_dir, api_url=API_URL, auth_headers=get_authentication_headers())


def main():
    parser = argparse.ArgumentParser(description="Upload a study to PKDB")
    parser.add_argument(
        "-s", help="directory of study", dest="study", type=str, required=True
    )
    parser.add_argument("--r", help="create reference json", action="store_true")
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
