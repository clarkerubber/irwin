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
			return user.checkPassword(password)
		return None

	def registerUser(name, password, privs=[]):
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