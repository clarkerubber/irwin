db.game.find().forEach(function(o) {
  db.game.update({
    _id: o.gameId
  }, {
    $unset: {
      white: true,
      black: true,
      userId: true
    }
  });
});