from default_imports import *

from modules.auth.Env import Env
from modules.auth.User import User, UserID, Username, Password
from modules.auth.Token import Token, TokenID
from modules.auth.Priv import Priv

from webapp.DefaultResponse import BadRequest

from flask import request, abort
from functools import wraps

Authable = TypeVar('Authable', User, Token)

Authorised = NewType('Authorised', bool)

AuthID = TypeVar('AuthID', UserID, TokenID)

class Auth(NamedTuple('Auth', [('env', Env)])):
    def loginUser(self, username: Username, password: Password) -> Tuple[Opt[User], Authorised]:
        """
        Attempts to log in a user.
        Returns True is successful.
        False if the user exists and the password is incorrect.
        None if the user does not exist.
        """
        user = self.env.userDB.byId(username)
        if user is not None:
            return (user, user.checkPassword(password))
        return (None, False)

    def registerUser(self, name: Username, password: Password, privs: List[Priv] = []) -> Opt[User]:
        """
        Will attempt to register a user.
        Returns User object if successful, otherwise None.
        """
        user = User.new(name, password, privs)
        if env.userDB.byId(user.id) is None:
            env.userDB.write(user)
            return user
        return None

    def authoriseTokenId(self, tokenId: TokenID, priv: Priv) -> Tuple[Opt[Token], Authorised]:
        """
        Given a tokenId, will check if the tokenId has priv.
        """
        token = self.env.tokenDB.byId(tokenId)
        if token is not None:
            return (token, token.hasPriv(priv))
        return (None, False)

    def authoriseUser(self, username: Username, password: Password, priv: Priv) -> Tuple[Opt[User], Authorised]:
        """
        Checks if user has priv in list of privs. 
        """
        user, loggedIn = self.loginUser(username, password)
        if user is not None:
            return (user, loggedIn and user.hasPriv(priv))
        return (None, False)

    def authoriseRequest(self, req: Opt[Dict], priv: Priv) -> Tuple[Opt[Authable], Authorised]:
        """
        Checks if a request is verified with priv.
        """
        if req is not None:
            # Attempt to authorise token first
            authReq = req.get('auth')
            if authReq is not None:
                tokenId = authReq.get('token')
                if tokenId is not None:
                    return self.authoriseTokenId(tokenId, priv)

                # Then attempt to authorise user/password
                username = authReq.get('username')
                password = authReq.get('password')

                if None not in [username, password]:
                    return self.authoriseUser(username, password, priv)

        return (None, False)

    def authoriseRoute(self, priv: Priv):
        """
        Wrap around a flask route and check it is authorised
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                json_obj = request.get_json(silent=True)
                authable, authorised = self.authoriseRequest(json_obj, priv)
                if authorised:
                    logging.info(f'{authable.name} has been authorised to {priv.permission}')
                    args_ = (authable,) + args
                    return func(*args_, **kwargs)
                if authable is not None:
                    logging.warning(f'UNAUTHORISED: {authable.name} has tried to perform an action requiring {priv.permission}')
                abort(BadRequest)
            return wrapper
        return decorator