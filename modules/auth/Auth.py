from default_imports import *

from modules.auth.Env import Env
from modules.auth.User import User, Username, Password
from modules.auth.Token import Token
from modules.auth.Priv import Priv

TokenID = NewType('TokenID', str)

Authable = TypeVar('Authable', User, Token)

@validated
class Auth(NamedTuple('Auth', [('env', Env)])):
    @validated
	def loginUser(self, username: Username, password: Password) -> Tuple[Opt[User], bool]:
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

    @validated
	def registerUser(self, name: str, password: Password, privs: List[Priv] = []) -> Opt[User]:
		"""
		Will attempt to register a user.
		Returns User object if successful, otherwise None.
		"""
		user = User.new(name, password, privs)
		if env.userDB.byId(user.id) is None:
			env.userDB.write(user)
			return user
		return None

    @validated
	def authoriseTokenId(self, tokenId: TokenID, priv: Priv) -> Tuple[Opt[Token], bool]:
		"""
		Given a tokenId, will check if the tokenId has priv.
		"""
		token = self.env.tokenDB.byId(tokenId)
		if token is not None:
			return (token, token.hasPriv(priv))
		return (None, False)

    @validated
	def authoriseUser(self, username: Username, password: Password, priv: Priv) -> Tuple[Opt[User], bool]:
		"""
		Checks if user has priv in list of privs. 
		"""
		user, loggedIn = self.loginUser(username, password)
		if user if not None:
			return (user, loggedIn and user.hasPriv(priv))
		return (None, False)

	def authoriseRequest(self, req, priv):
		"""
		req: Dict
		priv: String

		Checks if a request is verified with priv.
		"""
		if req is not None:
			tokenId = reg.get('auth', {}).get('token')
			if tokenId is not None:
				return self.authoriseTokenId(tokenId, priv)

			username = req.get('auth', {}).get('username')
			password = req.get('auth', {}).get('password')

			if None not in [username, password]:
				return self.authoriseUser(username, password, priv)

		return (None, False)