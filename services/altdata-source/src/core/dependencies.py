import os
from pathlib import Path
from typing import List, Dict, Any

import yaml
from pydantic import BaseModel


class RepoConfig(BaseModel):
    org: str
    repos: List[str]
    label: str


class ConfigLoader:
    """加载并解析 repositories.yaml 中的目标"""
    
    @classmethod
    def load_repositories(cls, file_path: str = None) -> List[RepoConfig]:
        if not file_path:
            # 默认加载 src/config/repositories.yaml
            base_dir = Path(__file__).resolve().parent.parent
            file_path = base_dir / "config" / "repositories.yaml"
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config file not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        repos = data.get("repositories", [])
        return [RepoConfig(**r) for r in repos]

    @classmethod
    def load_hardware_config(cls, file_path: str = None) -> Dict[str, Any]:
        if not file_path:
            base_dir = Path(__file__).resolve().parent.parent
            file_path = base_dir / "config" / "hardware.yaml"
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Hardware config file not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
