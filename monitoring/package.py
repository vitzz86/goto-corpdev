"""Include operational monitoring sources in each static release, excluding run artifacts."""
from pathlib import Path
import shutil

def package_monitoring(root):
    root=Path(root);source=root/'monitoring';destination=root/'dist/monitoring'
    shutil.copytree(source,destination,dirs_exist_ok=True,ignore=shutil.ignore_patterns('results','__pycache__','*.pyc'))
    workflows=root/'dist/.github/workflows';workflows.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source/'workflows/research-intake.yml',workflows/'research-intake.yml')
