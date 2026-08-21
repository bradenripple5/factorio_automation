import pyperclip

endstring = ("coal pickup | full")
for i in [0,7,8,15,16,1,6,9,14,17,2,5,10,18,3,4,11,12,19,21,20]:
	if i == 0 or i >9:
		number = str(i)
	else:
		number = "0"+str(i)

	endstring += f"\ncoal supply - advanced circuit base {number} | time | 5"

pyperclip.copy(endstring)