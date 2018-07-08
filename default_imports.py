## Typing and enforcing of types
from typing import NamedTuple, TypeVar, NewType, List, Dict, Tuple
from typing import Optional as Opt

from numpy import float16, float32, float64
from numpy import float as npfloat

Number = TypeVar('Number', int, float, npfloat, float16, float32, float64)

## Logging
import logging