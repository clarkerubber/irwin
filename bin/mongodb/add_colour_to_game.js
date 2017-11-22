db.gameAnalysis.find().forEach(function(o) {
  db.game.update({
    _id: o.gameId
  }, {
    $unset: {
      white: true,
      black: true
    },
    $set: {
      white: (o._id.split("/")[1] == "white"),
      userId: o.userId
    }
  });
});