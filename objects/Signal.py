from dataclasses import dataclass

@dataclass
class Signal:
    reference:str
    level:float
    num_breaks:int=0