# irwin
irwin is the AI that learns cheating patterns, marks cheaters, and assists moderators in assessing potential cheaters.

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
    "url": "https://en.lichess.org/",
    "token": "token"
  },
  "stockfish": {
    "threads": 4,
    "memory": 2048,
    "nodes": 4500000,
    "update": true
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
    "training": {
      "minStep": 10000,
      "incStep": 5000
    },
    "thresholds": {
      "averages": {
        "suspicious": 60,
        "verysuspicious": 75,
        "exceptional": 85,
        "legit": 40
      },
      "pvs": {
        "suspicious": 70,
        "legit": 35
      }
    }
  }
}
```

`conf/config.json` contains settings for stockfish, mongodb, tensorflow, lichess (authentication token and URL), etc...
### Build a database of analysed players
If you do not already have a database of analysed players, it will be necessary to analyse
a few hundred players to train the neural networks on.
`python3 main.py --no-assess --no-report`

### Train neural networks
`python3 main.py --learner --force-train --no-analyse`
This will force irwin to start training on the players that it has analysed. The `--no-analyse` flag will stop
irwin from analysing players with stockfish, and it will not assess players or post reports on them.

#### Debugging
If you see outputs like this where `True P: 0.0%` or `True N: 0.0%`
```
[[ 0.59259665  0.          1.          0.          1.          0.        ]
 [ 0.          0.          0.          0.          0.          1.        ]
 [ 0.          0.          0.          0.          0.          1.        ]
 ..., 
 [ 1.54029167  0.          1.          0.          1.          0.        ]
 [ 0.45083776  0.          1.          0.          1.          0.        ]
 [ 1.04098701  0.          1.          0.          1.          0.        ]]
Step: 37000
True P:   0.0% (0)
True N:   64.0% (320)
False P:  0.0% (0)
False N:  35.8% (179)
Indecise: 37.625% (301)
loss: 0.663807
eval: 0.588125
```
It means that the neural net was poorly initialised and it is not making useful predictions.
If this happens, stop irwin `ctrl+c` and go to the relevant models folder
`modules/irwin/models/[moves|chunks|pvs]` and delete its contents (leaving the `__init__.py`
if you intend to push to this git). Then start irwin back up with the same command.
It might take a few tries to get a good initialisation that looks like this.

```
[[ 0.50404608  0.          1.          0.          0.          1.        ]
 [ 1.43572056  0.          1.          0.          1.          0.        ]
 [ 0.59026158  0.71266842  0.          1.          0.          1.        ]
 ..., 
 [ 1.36209404  1.39978981  0.          1.          0.          1.        ]
 [ 0.75175393  0.          1.          0.          1.          0.        ]
 [ 0.          4.04198742  0.          1.          0.          1.        ]]
Step: 79000
True P:   89.20454545454545% (314)
True N:   75.84650112866817% (336)
False P:  10.511363636363637% (37)
False N:  23.927765237020317% (106)
Indecise: 0.875% (7)
loss: 0.38671
eval: 0.816875
```

Once you have a good initialisation, it shouldn't be necessary to redo this.

## Launching
```
python3 main.py [--quiet] [--learner] [--force-train] [--no-assess] [--no-analyse] [--no-report] [--update-all] [--test-only]
[--quiet] lower the amount of logging in the console
[--learner] this instance will reteach itself every 24 hours.
[--force-train] start training immediately (used in combination with [--learner]).
[--no-assess] do not pass analysed players through neural networks.
[--no-analyse] disables primary program. Will not process new players at all.
[--no-report] analyse players, but do not post reports to lichess (safe-mode)
[--update-all] instead of just getting the engine status of unsorted players, resort the entire database.
[--test-only] just and only test the performance of the neural networks on players.
```

For normal use in the command line `python3 main.py` is adequate.

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

### Terminology
- _Analysed_: Analysed by stockfish
- _Assessed_: Assessed by the neural network.
- _Analysis_: A class that _can_ be analysed.
