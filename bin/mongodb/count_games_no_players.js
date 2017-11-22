var without = 0;
var withg = 0;
db.game.find().forEach(function(o) {
  if (!o.hasOwnProperty("white") && !o.hasOwnProperty("black")) {
    without++;
  } else {
    withg++;
  }
});
print(without);
print(withg);