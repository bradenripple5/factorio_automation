class Fraction():
	def __init__(self,a,b=1):
		self.a = a
		self.b = b

	def __str__(self):
		return (f"{self.a}/{self.b}")
	def to_decimal(self):
		return self.a/self.b
	def multiply(self,x):
		self.a *=x
	def divide(self,x):
		self.b *=x
	def add(self,f):
		return Fraction(self.a*f.b + f.a * self.b, self.b * f.b)
	def subtract(self,f):
		g = Fraction(-f.a,f.b)
		return self.add(g)
if __name__ == "__main__":
	g = Fraction(5)
	f = Fraction(1,2)
	print(g)
	print(f)
	print(f.to_decimal())
	print( Fraction(2,3).add(Fraction(4,5)))
	print( Fraction(2,3).subtract(Fraction(4,5)))

