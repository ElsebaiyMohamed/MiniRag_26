import os
from helpers import get_settings, Settings

class BaseController:
    def __init__(self):
        self.app_settings: Settings = get_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.tenant_dir = self.__make_data_vault()
        
    def __make_data_vault(self):
        assets_dir = os.path.join(self.base_dir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        tenant_dir = os.path.join(assets_dir, 'files')
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir