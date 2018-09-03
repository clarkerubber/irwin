db.player.find({}).forEach(function(p) {
  db.analysedGame.find({userId: p._id}).forEach(function(g) {
    db.analysedGamePlayerPivot.update({
        _id: g._id
      }, {
        _id: g._id,
        userId: p._id,
        engine: p.engine,
        length: g.analysis.length
      }, {
        upsert: true
      }
    );
  });
});