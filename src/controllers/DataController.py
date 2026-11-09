import os
import re

from fastapi import UploadFile

from models.enums import ResponseSignal, ProcessingEnum
from .BaseController import BaseController


class DataController(BaseController):

    def __init__(self):
        super().__init__()
        self.size_scale = 1048576 # convert mg to bytes

    async def validate(self, file: UploadFile):

        if file.content_type not in self.app_settings.FILE_ALLOWED_EXTENTIONS:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [ProcessingEnum.TXT.value, ProcessingEnum.PDF.value]:
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
