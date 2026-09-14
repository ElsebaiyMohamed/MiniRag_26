import os
from .BaseController import BaseController

class ProjectController(BaseController):
    def __init__(self):
        super().__init__()
        
    def get_project_path(self, project_id):
        project_dir = self.join_path(self.tenant_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        return project_dir
    