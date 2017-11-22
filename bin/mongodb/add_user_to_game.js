db.playerAssessment.find().forEach(function(o) {
  var query = {};
  if (o.white) {
    query = {
      white: o.userId
    };
  } else {
    query = {
      black: o.userId
    };
  }
  db.game.update({
    _id: o.gameId
  },{
    $set: query
  });
});