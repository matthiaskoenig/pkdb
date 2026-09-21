"""File storage which overwrites existing files instead of renaming uploads."""

import os

from django.core.files.storage import FileSystemStorage


class OverwriteStorage(FileSystemStorage):
    """File storage backend that replaces an existing file of the same name."""

    def get_available_name(self, name, max_length=None):
        """Delete an existing file with the same name so it gets overwritten."""
        if os.path.exists(self.path(name)):
            os.remove(self.path(name))
        return name
