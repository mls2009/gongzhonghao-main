# This file makes the routers directory a Python package 
from . import browsers, accounts, settings
from .materials import router as materials_router
from .browsers import router as browsers_router
from .accounts import router as accounts_router
from .settings import router as settings_router

__all__ = [
    'materials_router',
    'browsers_router',
    'accounts_router',
    'settings_router'
]