db.game.find().forEach(function(o) {
  var len = o.pgn.length;
  var whiteLen = Math.ceil(len/2);
  var blackLen = Math.floor(len/2);
  var whiteBlurs = {
    nb: 0,
    bits: Array(whiteLen + 1).join('0')
  };
  var blackBlurs = {
    nb: 0,
    bits: Array(blackLen + 1).join('0')
  }
  db.game.update({
    _id: o._id
  }, {
    $set: {
      whiteBlurs: whiteBlurs,
      blackBlurs: blackBlurs
    }
  });
});