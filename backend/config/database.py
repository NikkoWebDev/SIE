import os
from typing import Generator
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "") or SUPABASE_SERVICE_KEY

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL debe estar definida")
if not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY debe estar definida")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_db() -> Generator[Client, None, None]:
    try:
        yield supabase_client
    finally:
        pass


def get_admin_db() -> Generator[Client, None, None]:
    try:
        yield supabase_admin_client
    finally:
        pass
