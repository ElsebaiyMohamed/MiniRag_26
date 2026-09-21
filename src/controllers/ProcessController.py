import os

from langchain_community.document_loaders import TextLoader, PyMuPDFLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter


from .BaseController import BaseController
from .ProjectController import ProjectController
from models.enums import ProcessingEnum




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
        if not self.file_exist_on_path(file_path=file_path):
            return None
        
        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding='utf-8')
        if file_ext == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        return None
    
    def get_file_content(self, file_id: str):
        loader = self._get_file_loader(file_id=file_id)
        if loader is not None:
            return loader.load()
        return None
    
    def process_file_content(self, file_content: list, chunk_size: int=100, overlap_size: int=20):
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap_size, length_function=len)
        
        file_text = [t.page_content for t in file_content]
        file_metadat = [t.metadata for t in file_content]
        
        chunks = text_spliter.create_documents(file_text, metadatas=file_metadat)
        return chunks
