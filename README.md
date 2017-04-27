# irwin
irwin is the AI that learns cheating patterns, marks cheaters, and assists moderators in assessing potential cheaters.

## Dependencies
Compatible with Python 3.x

### Python Libraries
- **pymongo** : `pip3 install pymongo`
- **python-chess** : `pip3 install python-chess`
- **numpy** : `pip3 install numpy`
- **tensorflow** : [tensorflow installation guide](https://www.tensorflow.org/versions/r0.10/get_started/os_setup)

### Libraries
- **mongodb** : [mongodb installation guide](https://docs.mongodb.com/manual/installation/)

## Configuring
Currently configuring the application is quite manual. The bot needs analysed players in the database to
train the neural networks, and it needs trained neural networks to assess players.

To work around this, assessing players with the neural network needs to be manually disabled, and training
the network also needs to be disabled. Once there's enough analysed players in the database training can be
turned back on, followed by assessing players.

The bot will retrain itself roughly every 24 hours to stay up to date with changing trends in cheating.

## Launching
`python3 main.py --quiet <Secret API Token> <Learner (1 or 0) = 1> <#Threads = 4> <Hash (Bytes) = 2048>`

### Terminology
- _Analysed_: Analysed by stockfish
- _Assessed_: Assessed by the neural network.
- _Analysis_: A class that _can_ be analysed.

## About
Irwin (named after Steve Irwin, the Crocodile Hunter) started as the name of the server that the original
cheatnet ran on (now deprecated). This is the successor to cheatnet.

Similar to cheatnet, it works on a similar concept of analysing the available PVs of a game to determine
the odds of cheating occurring.

This bot makes improvements over cheatnet by taking a dramatically more modular approach to software design.
`modules/core` contains most of the generic datatypes, BSON serialisation handlers and database interface
layers. It is also significantly faster due to a more simplified approach to using stockfish analysis.

`modules/irwin` contains the brains of irwin, this is where the tensorflow learning and application takes place.

Irwin has been designed so that `modules/irwin` can be replaced with other approaches to player assessment.

Using these modules in relation to lichess can be found in `main.py` and `modules/Api.py`

`Env.py` contains all of the tools to interact with lichess, irwin, and the database handlers.