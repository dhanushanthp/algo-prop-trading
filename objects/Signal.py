from dataclasses import dataclass

@dataclass
class Signal:
    reference:str
    level:float
    num_breaks:int=0


if __name__ == "__main__":
    obj1 = Signal("a", 0.343, 1)
    obj2 = Signal("a", 0.343, 2)
    output = [obj1, obj2]
    output.remove(obj1)
    print(output)