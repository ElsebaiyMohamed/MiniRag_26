import os
from random import choices as random_choice
from string import ascii_lowercase, digits

from helpers import get_settings, Settings

class BaseController:
    def __init__(self):
        self.app_settings: Settings = get_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.tenant_dir = self.__make_data_vault()
        
    def __make_data_vault(self):
        assets_dir = self.join_path(self.base_dir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        tenant_dir = self.join_path(assets_dir, 'files')
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir
    
    def _gen_rand_str(self, length: int=12):
        return ''.join(random_choice(ascii_lowercase + digits, k=length))
    
    def join_path(self, prefix, suffix):
        return os.path.join(prefix, suffix)
    
    def file_exist_on_path(self, file_path) -> bool:
        return os.path.exists(file_path)
