import os
from typing import Generator
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL y SUPABASE_KEY deben estar definidas")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_db() -> Generator[Client, None, None]:
    try:
        yield supabase
    finally:
        pass
