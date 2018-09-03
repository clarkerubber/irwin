from default_imports import *

Permission = NewType('Permission', str)

Priv = NamedTuple('Priv', [
        ('permission', Permission)
    ])

RequestJob = Priv('request_job') # client can request work
CompleteJob = Priv('complete_job') # client can post results of work
PostJob = Priv('post_job') # lichess can post a job for analysis