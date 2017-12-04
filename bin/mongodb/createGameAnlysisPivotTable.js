db.player.find({}).forEach(function(p) {
  db.gameAnalysis.find({userId: p._id}).forEach(function(g) {
    db.gameAnalysisPlayerPivot.update({
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