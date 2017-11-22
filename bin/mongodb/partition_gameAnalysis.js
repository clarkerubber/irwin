db.gameAnalysis.find({}).forEach(function(o) {
  db.gameAnalysis.update({
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