"""Some http/socket related utilities.
"""
import socket
import requests

class HTTPAdapterWithSocketOptions(requests.adapters.HTTPAdapter):
    """A helper adapter to set socket options on the socket requests will use.
    """
    def __init__(self, *args, **kwargs):
        self.socket_options = kwargs.pop("socket_options", None)
        super(HTTPAdapterWithSocketOptions, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        if self.socket_options is not None:
            kwargs["socket_options"] = self.socket_options
        super(HTTPAdapterWithSocketOptions, self).init_poolmanager(*args, **kwargs)


def get_keepalive_adapter():
    return HTTPAdapterWithSocketOptions(
        socket_options=[(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    )

def get_requests_session_with_keepalive():
    adapter = get_keepalive_adapter()
    s = requests.session()
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s
