
from cmath import sqrt


class Point:
    def __init__(self, a, b):
        self._a = a
        self._b = b

    def get_a(self):
        return self._a
    
    def get_b(self):
        return self._b

    def move(self, newA, newB):
        self._a = newA
        self._b = newB

    def distance(self, pointB):
        return sqrt( (pointB.get_a() - self._a)^2 + (pointB.get_b() - self._b)^2 )
    
    def __str__(self):
        return f"puntoA: {self._a}, puntoB: {self._b}"

