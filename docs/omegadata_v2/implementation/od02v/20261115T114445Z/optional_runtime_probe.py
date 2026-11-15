import json
import shutil
from pathlib import Path

base=Path.home()/".local/share/uv/python"
print(json.dumps({"linux_python311_on_path":shutil.which("python3.11"),
    "linux_python312_on_path":shutil.which("python3.12"),
    "existing_uv_runtime_directory_names":[p.name for p in base.iterdir() if p.is_dir()] if base.is_dir() else [],
    "no_install_performed":True},indent=2))
