



class Calculator:
    def __init__(self, nome):
        self._nome = nome

    def add(self, a, b):
        return a + b
    def sub(self, a, b):
        return a - b
    def mul(self, a, b):
        return a * b
    def div(self, a, b):
        return a / b
    


calc = Calculator('booo')
risultato = calc.add(3, 5)
print(risultato)

c=Calculator('Casio')
print(c.add(2,3))
print(c.sub(2,3))
print(c.mul(2,3))
print(c.div(2,3))