# irwin
irwin is the AI that learns cheating patterns, marks cheaters, and assists moderators in assessing potential cheaters.

![screenshot of Irwin report](https://i.imgur.com/UcVlDK3.png)

![screenshot of companion WebApp](https://i.imgur.com/LQtSQAh.png)

## Dependencies
Compatible with Python 3.x

### Python Libraries
```sh
pip3 install pymongo python-chess numpy requests
```
- **tensorflow** : [tensorflow installation guide](https://www.tensorflow.org/install)

### Database
- **mongodb** : [mongodb installation guide](https://docs.mongodb.com/manual/installation/)

## Configuring
### Create `conf/config.json`
```javascript
{
  "api": {
    "url": "https://lichess.org/",
    "token": "token"
  },
  "stockfish": {
    "threads": 4,
    "memory": 2048,
    "nodes": 4500000,
    "update": false
  },
  "db": {
    "host": "localhost",
    "port": 27017,
    "authenticate": false,
    "authentication": {
      "username": "username",
      "password": "password"
    }
  },
  "irwin": {
    "train": {
      "batchSize": 5000,
      "cycles": 80
    }
  }
}
```

`conf/config.json` contains config for stockfish, mongodb, tensorflow, lichess (authentication token and URL), etc...
### Build a database of analysed players
If you do not already have a database of analysed players, it will be necessary to analyse
a few hundred players to train the neural networks on.
`python3 main.py --no-assess --no-report`

## About
Irwin (named after Steve Irwin, the Crocodile Hunter) started as the name of the server that the original
cheatnet ran on (now deprecated). This is the successor to cheatnet.

Similar to cheatnet, it works on a similar concept of analysing the available PVs of a game to determine
the odds of cheating occurring.

This bot makes improvements over cheatnet by taking a dramatically more modular approach to software design.
`modules/core` contains most of the generic datatypes, BSON serialisation handlers and database interface
layers. It is also significantly faster due to a simplified approach to using stockfish analysis.

`modules/irwin` contains the brains of irwin, this is where the tensorflow learning and application takes place.

Irwin has been designed so that `modules/irwin` can be replaced with other approaches to player assessment.

`Env.py` contains all of the tools to interact with lichess, irwin, and the database handlers.

`main.py` covers accessing the lichess API (`modules/Api.py`) via Env to get player data; pulling records from mongodb,
analysing games using stockfish, assessing those games using tensorflow and then posting the final assessments.
