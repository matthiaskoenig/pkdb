from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from starlette.concurrency import run_in_threadpool

from pkdb_server.services.authentication import AuthenticationFailed, authenticate_token


class DatabaseTokenVerifier(TokenVerifier):
    def __init__(self, session_factory):
        super().__init__(required_scopes=["pkdb"])
        self.session_factory = session_factory

    def principal(self, raw):
        with self.session_factory.begin() as session:
            return authenticate_token(raw, session)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            principal = await run_in_threadpool(self.principal, token)
        except AuthenticationFailed:
            return None
        return AccessToken(
            token=token, client_id=str(principal.user_id), scopes=["pkdb"]
        )

    def current_principal(self):
        token = get_access_token()
        if token is None:
            raise AuthenticationFailed("Authentication required")
        # Recheck active/role/revocation state at tool execution, not only at initialize.
        return self.principal(token.token)
