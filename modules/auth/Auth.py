from modules.auth.User import User
from collections import namedtuple

class Auth(namedtuple('Auth', ['env'])):
	def loginUser(self, username, password):
		"""
		username: String
		password: String (raw password)
		
		Attempts to log in a user.
		Returns True is successful.
		False if the user exists and the password is incorrect.
		None if the user does not exist.
		"""
		user = self.env.userDB.byId(username)
		if user is not None:
			return (user, user.checkPassword(password))
		return (None, False)

	def registerUser(self, name, password, privs=[]):
		"""
		name: String
		password: String
		privs: List[Priv]

		Will attempt to register a user.
		Returns User object if successful, otherwise None.
		"""
		user = User.new(name, password, privs)
		if env.userDB.byId(user.id) is None:
			env.userDB.write(user)
			return user
		return None

	def authoriseTokenId(self, tokenId, permission):
		"""
		tokenId: String
		permission: String

		Given a tokenId, will check if the tokenId has permission.
		"""
		token = self.env.tokenDB.byId(tokenId)
		if token is not None:
			return (token, token.hasPermission(permission))
		return (None, False)

	def authoriseUser(self, username, password, permission):
		"""
		username: String
		password: String
		permission: String

		Checks if user has permission in list of privs. 
		"""
		user, loggedIn = self.loginUser(username, password)
		if user if not None:
			return (user, loggedIn and user.hasPermission(permission))
		return (None, False)

	def authoriseRequest(self, req, permission):
		"""
		req: Dict
		permission: String

		Checks if a request is verified with permission.
		"""
		tokenId = reg.get('auth', {}).get('token')
		if tokenId is not None:
			return self.authoriseTokenId(tokenId, permission)

		username = req.get('auth', {}).get('username')
		password = req.get('auth', {}).get('password')

		if None not in [username, password]:
			return self.authoriseUser(username, password, permission)
