import os
from random import choices as random_choice
from string import ascii_lowercase, digits

from helpers import get_settings, Settings

class BaseController:
    def __init__(self):
        self.app_settings: Settings = get_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.assets_dir = self.__make_data_vault()
        self.tenant_dir = self.__make_tenant_vault()
        self.db_dir = self.__make_database_vault()
        
    def __make_data_vault(self):
        assets_dir = self.join_path(self.base_dir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        return assets_dir
    def __make_tenant_vault(self):
        tenant_dir = self.join_path(self.assets_dir, 'files')
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir
    def __make_database_vault(self):
        databaset_dir = self.join_path(self.assets_dir, 'vector_database')
        os.makedirs(databaset_dir, exist_ok=True)
        return databaset_dir
    def _gen_rand_str(self, length: int=12):
        return ''.join(random_choice(ascii_lowercase + digits, k=length))
    
    def join_path(self, prefix, suffix):
        return os.path.join(prefix, suffix)
    
    def file_exist_on_path(self, file_path) -> bool:
        return os.path.exists(file_path)
    def get_database_path(self, db_name: str):
        db_path = self.join(self.db_dir, db_name)
        os.makedirs(db_path, exist_ok=True)
        return db_path
