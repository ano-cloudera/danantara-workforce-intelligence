#!/usr/bin/env python3
import os, httpx
base = os.getenv('BACKEND_BASE_URL','http://127.0.0.1:8000')
print(httpx.get(base+'/health', timeout=5).json())
print(httpx.get(base+'/api/v1/positions', timeout=5).json())
