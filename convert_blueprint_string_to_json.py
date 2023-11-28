import json, zlib, base64
s = '0eNp9j8EKgzAQRP9lzhHUQrX5lVJKTBe7YNaQxFIR/70xvfTUy8Iss29mNwzTQj6wJOgNbGeJ0NcNkUcx07FLqydocCIHBTHuUCZGcsPEMlbO2CcLVSfsCiwPekM3+02BJHFi+vKKWO+yuIFCNvwnKfg55uNZjgYZWCuseeaEQJZLITt7T6GyZpgIR15pqH8eUnhRiAVy7ru27ZtL3bX7/gEshFHQ'
s = '0eNqNkulugzAQhN9lf2MpkJtXqaLImC1Z1QfxURVFvHvXJKWVcqi/LOPx59lhLtDohL0nG6G+AClnA9RvFwjUWanztzj0CDVQRAMFWGnyToaAptFkO2GkOpFFsYSxALItfkFdjocC0EaKhFfetBmONpkGPQtmksGWkhGoUUVPSvROI7/Tu8CXnc0OGCj4wpCXcSzuYNUMC1GqD0E2oI98codZ/FAKaMnzi9PR6gFz+W/mK2ermaJdRyHyfOqEIQqP58TrC17FHm+q4ztpll6DvCW8m8nknRW9ljHHplzKf7LKXm7K/axsZGTM8Ctbj4cHptfPTIfovOzwaazVowg2rzvzhFVO0yuaqieVSibxhM5DLtZUxfpPcwv45Hgmxma3rapduV9s2c03F+72IQ=='
# with open("fiveassemblers_string") as f:
# 	s = f.read()
filename = "4trackcurve"
with open(filename) as f:
	s = f.read()
string = zlib.decompress(base64.b64decode(s[1:])).decode("utf-8")
# print(string)
# string = (zlib.decompress(base64.b64decode(s[1:])).decode("utf-8"))

# inverse = base64.b64encode(zlib.compress(bytes(string,"utf-8")))

# print(inverse)
# print("****")
d = json.loads(string)
print(json.dumps(d,indent=2))
with open(filename+".json","w+") as f:
	f.write(string)

# inverse = json.dumps(string)
# print(inverse)