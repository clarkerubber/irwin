db.game.find({}).forEach(function(o) {
  if (!Array.isArray(o.pgn)) {
    db.game.update({
      _id: o._id
    }, {
      $set: {
        pgn: o.pgn.split(" ")
      }
    });
  }
});