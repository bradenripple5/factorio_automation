import random
characters = [chr(j) for j in range(33,127)]
print(characters)
print("".join([random.choice(characters) for i in range(15)]))