import random
digits =  [chr(j) for j in [i for i in range(ord('A'),ord('Z')+1)]+[i for i in range(ord('a'),ord('z')+1)]+[i for i in range(ord('0'),ord('9'))]]

def create_six_digit_id():
	try:
		with open("six_digit_ids","r") as f:
			all_ids = f.read().split("\n")
	except:
		with open("six_digit_ids","w+") as f:
			all_ids = []

	print(all_ids)
	new_six_digit_id = "".join([random.choice(digits) for i in range(6)])
	if new_six_digit_id not in all_ids:
		all_ids.append(new_six_digit_id)
		with open("six_digit_ids","w+") as f:
			f.write("\n".join(all_ids))
		return new_six_digit_id
	else:
		return create_six_digit_id()
print(create_six_digit_id())