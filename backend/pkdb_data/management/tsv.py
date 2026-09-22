"""Helper function which creates TSV files from the spread sheet."""

import logging
import re
import time
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def build_tsvs(path_xlsx: Path) -> bool:
    """Create TSV files from excel sheets.

    :param path_xlsx: path to excel file
    :return: success flag
    """
    start_time = time.time()
    if path_xlsx.suffix != ".xlsx":
        msg = f"excel file has wrong suffix: file_path = {path_xlsx}"
        logger.error(msg)
        return False
    try:
        xlsx_data = pd.read_excel(path_xlsx, sheet_name=None, skiprows=[0], comment="#")

    except Exception as err:
        logger.error(
            "Problems reading xlsx file. Probably stored in incorrect format. "
            "Make sure files are in 'Excel 2007-365 (.xlsx).'"
        )
        logger.info(str(err))
        return False
    success = True

    uploaded_sheets = []

    for sheet_name, df in xlsx_data.items():
        for c in df.columns:
            if not isinstance(c, str):
                msg = f"In sheet <{sheet_name}> the columns contain non-string values:{c} "

                logger.error(msg)

        # FIXME: we said no Unnamed columns! Not just throwing them away
        header = [c for c in df.columns if "Unnamed:" not in c]
        df = df[header]

        tsv_file_name = f".{path_xlsx.stem}_{sheet_name}.tsv"
        tsv_path = path_xlsx.with_name(tsv_file_name)
        sheet_success = _validate_sheet_name(sheet_name, path_xlsx.stem)
        if not df.empty and sheet_success:
            # FIXME !!!! Remove this
            # see https://github.com/pandas-dev/pandas/pull/39547
            df = df.dropna(axis=0, how="all")
            # FIXME !!!! Remove this

            sheet_success = validate_excel_sheet(df, sheet_name, path_xlsx.stem)

            df.to_csv(tsv_path, sep="\t", index=False, na_rep="NA")
            uploaded_sheets.append(sheet_name)

        success = sheet_success and success

    if success:
        duration = time.time() - start_time
        logger.info("- %.2f [s] : Created TSVs %s", duration, sorted(uploaded_sheets))
    return success


def validate_excel_sheet(df: pd.DataFrame, sheet_name: str, study_id: str) -> bool:
    """Validate given excel sheet.

    :param df: loaded pandas.DataFrame
    :param sheet_name: name of spreadsheet
    :param study_id: study identifier
    :return: boolean validation status
    """
    validations: list[bool] = [
        validate_no_empty_rows(df, sheet_name, study_id),
        validate_format(df, sheet_name, study_id),
        validate_popular_suffix(list(df.columns), sheet_name, study_id),
        validate_forbidden_prefix(list(df.columns), sheet_name, study_id),
        validate_unique_suffix(list(df.columns), sheet_name, study_id),
    ]

    return all(validations)


def validate_no_empty_rows(df: pd.DataFrame, sheet_name: str, study_id: str) -> bool:
    """Validate that no empty lines exist in sheet."""
    if len(df.dropna(how="all").index) < len(df.index):
        msg = (
            f"Sheet <{sheet_name}> of file <{study_id}.xlsx> contain "
            f"empty lines. Remove the line or add a '#' as the first character in the line."
        )
        logger.warning(msg)

    return True


def validate_format(df: pd.DataFrame, sheet_name: str, study_id: str) -> bool:
    """Validate excel format."""
    is_valid = True
    for column_index, column_name in enumerate(df.columns):
        if column_index == 0:
            if not _validate_first_column_name(column_name, sheet_name, study_id):
                is_valid = False
            if not _validate_first_column_id(df, sheet_name, study_id):
                is_valid = False

        if not _validate_lower_cause(column_name, study_id, sheet_name, column_index):
            is_valid = False
        if not _validate_special_characters(
            column_name, study_id, sheet_name, column_index
        ):
            is_valid = False
        if not _validate_no_whitespace(column_name, study_id, sheet_name, column_index):
            is_valid = False
    return is_valid


def validate_popular_suffix(
    column_names: Iterable[str], sheet_name: str, study_id: str
) -> bool:
    """Validate popular suffixes.

    * All headers (columns) in the TSVs must be lowercase,
      only contain [a-z, _ ] (i.e, no special characters and no whitespace).
    * if a column ends with "*_unit" then the * column must exist in the
      columns, e.g. if `cpep_unit` is a field `cpep` must exist
    * if a column ends with "*_sd" then the * column must exist in the
      columns, e.g. if `cpep_sd` is a field `cpep` must exist
    * if a column ends with "*_se" then the * column must exist in the
      columns, e.g. if `cpep_se` is a field `cpep` must exist
    :param column_names:
    :param sheet_name:
    :param study_id:
    :return:
    """
    popular_suffixes = ["_cv", "_se", "_sd", "_min", "_max", "_unit"]
    correct_column_name = True
    for suffix in popular_suffixes:
        required_column_names = [
            column_name[: -len(suffix)]
            for column_name in column_names
            if column_name.endswith(suffix)
        ]
        for column_name in required_column_names:
            if column_name not in column_names:
                msg = (
                    f"If a column was named with the following pattern: "
                    f"<*{suffix}>. Then the column name <*> is required. "
                    f"In sheet <{sheet_name}> of file <{study_id}.xlsx> a "
                    f"column <{column_name + suffix}> was defined but "
                    f"not <{column_name}>."
                )
                logger.error(msg)
                correct_column_name = False

    return correct_column_name


def validate_unique_suffix(
    column_names: Iterable[str], sheet_name: str, study_id: str
) -> bool:
    """Check uniqueness of suffixes.

    This catches duplications such as `mean_sd` and `sd`
    """
    popular_suffixes = ["_cv", "_se", "_sd", "_min", "_max", "_unit"]
    col_names_set = set(column_names)

    correct_column_name: bool = True
    for suffix in popular_suffixes:
        if (f"mean{suffix}" in col_names_set) and (suffix[1:] in col_names_set):
            msg = (
                f"The column names `mean{suffix}` and `{suffix[1:]}` may not exist "
                f"in the same sheet. Rename the `mean{suffix}` column."
            )
            logger.error(msg)
            correct_column_name = False

    return correct_column_name


def validate_forbidden_prefix(
    column_names: Iterable[str], sheet_name: str, study_id: str
) -> bool:
    """Validate forbidden column prefixes.

    Forbidden column names are [ unit_*, sd_*, se_*, cv_* ]
    These are often incorrectly encoded: unit_time should be time_unit
    """
    forbidden_prefix = ["unit_", "sd_ ", "se_", "cv_"]
    correct_column_name = True
    for column_name in column_names:
        for prefix in forbidden_prefix:
            if column_name.startswith(prefix):
                msg = (
                    f"column name are not allowed to start with <{prefix}*>. "
                    f"In sheet <{sheet_name}> of file <{study_id}.xlsx> a "
                    f"column <{column_name}> was defined."
                )
                logger.error(msg)
                correct_column_name = False

    return correct_column_name


def _validate_first_column_name(
    first_column: str, sheet_name: str, study_id: str
) -> bool:
    """Validate that first column is study."""
    if first_column != "study":
        msg = (
            f"Name of first column must be 'study'. "
            f"In sheet <{sheet_name}> of file <{study_id}.xlsx> first "
            f"column is <{first_column}>."
        )
        logger.error(msg)
        return False
    return True


def _validate_special_characters(
    column_name: str, study_id: str, sheet_name: str, column_index: int
) -> bool:
    """Validate that no special characters are in column names."""
    if not re.match("^[a-zA-Z0-9_]*$", column_name):
        msg = (
            f"No special characters or whitespace allowed in column names. "
            f"Allowed characters are 'a-zA-Z0-9_'."
            f"In sheet <{sheet_name}> of file <{study_id}.xlsx> "
            f"{column_index}th column is <{column_name}>."
        )
        logger.error(msg)
        return False
    return True


def _validate_lower_cause(
    column_name: str, study_id: str, sheet_name: str, column_index: int
) -> bool:
    """Validate that column name is lower case."""
    if column_name != column_name.lower():
        msg = (
            f"Column names in all sheets must be lower case'. "
            f"In sheet <{sheet_name}> of file <{study_id}.xlsx> {column_index}th "
            f"column is <{column_name}>."
        )
        logger.error(msg)
        return False
    return True


def _validate_no_whitespace(
    column_name: str, study_id: str, sheet_name: str, column_index: int
) -> bool:
    """Validate that  column name has no white space."""
    if " " in column_name:
        msg = (
            f"Column names in all sheets must not have any white space "
            f"characters. In sheet <{sheet_name}> of file "
            f"<{study_id}.xlsx> {column_index}th column is <{column_name}>."
        )
        logger.error(msg)
        return False
    return True


def _validate_first_column_id(df: pd.DataFrame, sheet_name: str, study_id: str) -> bool:
    """Validate first column contains study id."""
    if "study" not in df.columns:
        # message by different validation rule
        return False
    if not all(df["study"] == study_id):
        msg = (
            f"'Study' column must contain the study id. "
            f"First column in sheet <{sheet_name}> in <{study_id}.xlsx> "
            f"contains <{df['study'].unique()}>."
        )
        logger.error(msg)
        return False
    return True


def _validate_sheet_name(sheet_name: str, study_id: str) -> bool:
    """Validate column name starts with allowed prefixes ."""
    supported_prefixes = ("Tab", "Fig")
    if not sheet_name.startswith(supported_prefixes):
        msg = (
            f"Invalid sheet name <{sheet_name}> in <{study_id}.xlsx>. "
            f"Sheet name must start with: <{supported_prefixes}>"
        )
        logger.error(msg)
        return False
    return True
