db.analysedGame.find({}).forEach(function(o) {
  db.analysedGame.update({
    _id: o._id
  }, {
    $set: {
      analysis: o.analysedMoves
    },
    $unset: {
      assessedMoves: true,
      assessedChunks: true,
      activation: true,
      pvActivation: true,
      moveChunkActivation: true,
      analysedMoves: true
    }
  });
});