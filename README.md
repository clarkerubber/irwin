# irwin
irwin is the AI that learns cheating patterns, marks cheaters, and assists moderators in assessing potential cheaters.

## Dependencies
Compatible with Python 2.7+ and Python 3.5+

### Python Libraries
- **pymongo** : `pip3 install pymongo`
- **python-chess** : `pip3 install python-chess`
- **numpy** : `pip3 install numpy`
- **tensorflow** : [tensorflow installation guide](https://www.tensorflow.org/versions/r0.10/get_started/os_setup#pip_installation)

### Libraries
- **mongodb** : `apt install mongodb`

## Launching
`python3 main.py --quiet <Secret API Token> <Learner (1 or 0) = 1> <#Threads = 4> <Hash (Bytes) = 2048>`
