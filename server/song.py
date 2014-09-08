class Song:
	def __init__(self, id, title, user):
		self.id = id
		self.title = title
		self.up_votes = 0
		self.down_votes = 0
		self.balance = 0
		self.path = ''
		self.user = user

	def up_vote(self):
		self.up_vote += 1

	def down_vote(self):
		self.down_vote -= 1

	def get_balance(self):
		return self.up_votes - self.down_votes

	def __str__(self):
		return "%s(%s)" % (self.title, self.id)