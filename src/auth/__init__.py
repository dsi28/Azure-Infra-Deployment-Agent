"""
Azure authentication module for the Infrastructure Agent.
"""

from .azure_auth import (
    AzureAuthenticator,
    AuthenticationResult,
    AuthenticationMethod,
    create_azure_authenticator,
)

__all__ = [
    "AzureAuthenticator",
    "AuthenticationResult", 
    "AuthenticationMethod",
    "create_azure_authenticator",
]