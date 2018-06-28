from collections import namedtuple

class Auth(namedtuple('Auth', ['env'])):
	def loginUser(self, username, password):
		user = self.env.userDb.byId(username)
		if user is not None:
			return user.checkPassword(password)