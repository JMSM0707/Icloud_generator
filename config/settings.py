import configparser
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = Path("config.ini")
        
        if not self.config_file.exists():
            self._create_default_config()
        
        self.config.read(self.config_file)
    
    def _create_default_config(self):
        self.config["DEFAULT"] = {
            "max_concurrent_tasks": "5",
            "delay_hours": "1",
            "time_between_accounts": "5",
            "max_retries": "3",
            "retry_delay": "2",
            "cookie_file": "cookie.txt",
            "generated_emails_file": "generated_emails.txt",
            "backup_dir": "backups",
            "timezone": "Europe/Moscow",
            "label": "rtuna's gen",
            "base_url_v1": "https://p68-maildomainws.icloud.com/v1/hme",
            "base_url_v2": "https://p68-maildomainws.icloud.com/v2/hme"
        }
        
        with open(self.config_file, "w") as f:
            self.config.write(f)
    
    def get(self, section: str, key: str) -> Any:
        return self.config.get(section, key)
    
    def getint(self, section: str, key: str) -> int:
        return self.config.getint(section, key)
    
    def getfloat(self, section: str, key: str) -> float:
        return self.config.getfloat(section, key)
    
    def getboolean(self, section: str, key: str) -> bool:
        return self.config.getboolean(section, key)
    
    @property
    def params(self) -> Dict[str, str]:
        return {
            "clientBuildNumber": "2413Project28",
            "clientMasteringNumber": "2413B20",
            "clientId": "",
            "dsid": "",
        }

config = Config()