class X():
	def f(self):
		b  = 1
		def g():
			nonlocal b
			b+=1
			return b
		return g()
x = X()
print(x.f())