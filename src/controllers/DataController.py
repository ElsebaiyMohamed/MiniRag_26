import os
import re
from pathlib import Path

from fastapi import UploadFile

from ingestion.exceptions import UnsupportedFileType
from ingestion.loaders import LoaderRegistry
from models.enums import ResponseSignal
from .BaseController import BaseController


class DataController(BaseController):

    def __init__(self, loader_registry: LoaderRegistry):
        super().__init__()
        self.loader_registry = loader_registry
        self.size_scale = 1048576 # convert mg to bytes

    async def validate(self, file: UploadFile):

        try:
            loader = self.loader_registry.for_path(
                Path(file.filename or "")
            )
        except UnsupportedFileType:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

        mime_type = (file.content_type or "").split(";")[0].strip().lower()

        loader_mime_types = {
            value.lower() for value in loader.mime_types
        }

        allowed_mime_types = {
            value.lower()
            for value in self.app_settings.FILE_ALLOWED_EXTENTIONS
        }

        # The MIME type must belong to the loader selected by extension,
        # and it must also be present in the configured allowlist.
        if (
            mime_type not in loader_mime_types
            or mime_type not in allowed_mime_types
        ):
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

        if file.size > self.app_settings.FILE_MAX_SIZE_IN_MB * self.size_scale:
            return False, ResponseSignal.FILE_SIZE_EXCEEDED.value

        return True, ResponseSignal.FILE_VALIDATED_SUCCESS.value


    def gen_unique_filename(self, org_filename, project_path):
        flage = True
        i = 1
        while flage:
            rand_filename = self._gen_rand_str(length=i)
            clean_filename = self.__cleaned_filename(org_filename)
            clean_filename = rand_filename + '_' + clean_filename
            if os.path.exists(self.join_path(project_path, clean_filename)):
                i += 1
                continue

            flage = False

        return clean_filename

    def __cleaned_filename(self, filename: str):
        return re.sub(r'[^\w.]', '', filename.strip()).replace(' ', '_')
