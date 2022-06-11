import logging

from channels.middleware import BaseMiddleware
from knox.models import AuthToken
from knox.settings import CONSTANTS

from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


HEADER_NAME = 'authorization'
TOKEN_NAME = 'token'
SEC_WEBSOCKET_PROTOCOL = 'sec-websocket-protocol'
ACCESS_TOKEN_NAME = 'access_token'


@database_sync_to_async
def get_user(token_key):
    try:
        token = AuthToken.objects.get(
            token_key=token_key[:CONSTANTS.TOKEN_KEY_LENGTH]
        )
        return token.user
    except AuthToken.DoesNotExist:
        return None


def extract_from_auth_header(value):
    try:
        token_identifier, token_value = value.split(' ')
        if token_identifier:
            token_identifier = token_identifier.strip().lower()
        if token_identifier == TOKEN_NAME:
            return token_value.strip()
    except ValueError:
        logger.warning(
            f"Poorly formatted Authorization header {value}"
        )
        return None


def extract_from_sec_websocket_protocol_header(value):
    try:
        token_access_identifier, token_value = value.split(',')
        if token_access_identifier:
            token_access_identifier = token_access_identifier.strip().lower()
        if token_access_identifier == ACCESS_TOKEN_NAME:
            return token_value.strip()
    except ValueError:
        logger.warning(
            f"Poorly formatted Sec-WebSocket-Protocol header {value}"
        )
        return None


def extract_token(headers):
    """
    Returns token from list of headers

    #
    #  header_name    token_name   token_value
    #  Authorization: Token        <token>
    #
    """
    for _key, _value in headers:
        key = _key.decode().lower()
        value = _value.decode()
        if key == HEADER_NAME:
            return extract_from_auth_header(value)
        if key == SEC_WEBSOCKET_PROTOCOL:
            return extract_from_sec_websocket_protocol_header(value)

    return None


class TokenAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        token_key = extract_token(headers=scope['headers'])

        if token_key is None:
            scope['user'] = None
        else:
            scope['user'] = await get_user(token_key)

        return await super().__call__(scope, receive, send)
