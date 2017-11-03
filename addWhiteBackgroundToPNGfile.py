import os
import subprocess

# Uses ImageMagick's convert command. Make sure it is installed in the system.
# Will set background color to white and remove alpha layer

input = "/mnt/d/Desktop/New folder"
output = f"{input}/whiteBackground"
removeAlpha = True

try:
	os.mkdir(output)
except:
	pass
	
for file in os.listdir(input):
	if file.endswith('png'):
		if removeAlpha:
			subprocess.run(['convert', os.path.join(input, file), '-background', 'white', '-alpha', 'remove', os.path.join(output, file)])
		else:
			subprocess.run(['convert', os.path.join(input, file), '-background', 'white', os.path.join(output, file)])

