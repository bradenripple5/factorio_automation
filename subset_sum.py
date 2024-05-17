#subset_sum.py
import random
pops = []
total = 10**8
while sum(pops) != 10**8:
	nextval = random.randint(10**6,10**7)
	if nextval > total:
		pops.append(total)
		total = 0
	else:
		pops.append(nextval)
		total -= nextval
print(pops)
print(sum(pops))

pops = sorted(pops)[:][::-1]
print(pops)
