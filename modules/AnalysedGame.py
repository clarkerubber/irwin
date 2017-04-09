class AnalysedGame:
  def __init__(self, game, playerAssessment):
    self.game = game
    self.playerAssessment = playerAssessment

  def __str__(self):
    return str(self.game) + "\n" + str(self.playerAssessment)

  def userId(self):
    return self.playerAssessment.userId

  def gameId(self):
    return self.game.id