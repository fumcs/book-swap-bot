from alembic.config import Config
from alembic.command import upgrade
from pathlib import Path
import asyncio

def _run_migrations():
    conf_path = Path(__file__).parent/'alembic'/'alembic.ini'
    conf = Config(str(conf_path))
    upgrade(conf, 'head')

async def run_migrations():
    await asyncio.get_running_loop().run_in_executor(None, _run_migrations)