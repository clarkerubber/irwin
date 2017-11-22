db.playerAnalysis.find({}).forEach(function(o) {
  db.player.insert({
    _id: o._id,
    titled: o.titled,
    engine: o.engine,
    gamesPlayed: o.gamesPlayed,
    closedReports: o.closedReports,
    date: o.date
  });
});