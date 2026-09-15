import os

from langchain_community.document_loaders import TextLoader, PyMuPDFLoader 

from .BaseController import BaseController
from .ProjectController import ProjectController
from models import ProcessingEnum




class ProcessController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()
        
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(self.project_id)
        
    def _get_file_ext(self, file_id: str):
        return os.path.splitext(file_id)[-1]
    
    def _get_file_loader(self, file_id: str):
        file_ext = self._get_file_ext(file_id=file_id)
        file_path = self.join_path(self.project_path, file_id)
        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding='utf-8')
        if file_ext == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        return None
    
    def get_file_content(self, file_id: str):
        loader = self._get_file_loader(file_id=file_id)
        return loader.load()
        
