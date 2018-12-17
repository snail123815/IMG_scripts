from ij import IJ
import csv
import os
from time import strftime
import ij.gui

# Take care of total path and numbers!!!!!!!
working_path = 'F:/20170627_sco1839'
max_img_num = 118
path_name = working_path.split('/')[-1]
target_path = 'd:/WORKs/Project_Sporulation/Pictures/%s_scanner'%path_name

os.chdir(working_path)
print("Working at: %s"%os.getcwd())
print("Target dir: %s"%target_path)


IJ.run("Set Measurements...", "mean redirect=None decimal=4")
IJ.run("Clear Results")



## change file name
#for i in range(1,max_img_num+1):
#	try:
#		filename = 'img_%s_cropped.jpg'%str(i).zfill(2)
#		newname = 'img_%s_cropped.jpg'%str(i).zfill(3)
#		os.rename(filename, newname)
#	except:
#		print('img_%s_cropped.jpg is not in the folder'%str(i).zfill(2))
#		break


# Get positions for measurment into a list of 4 number lists
macro_text = '''
makePolygon(1000,1128,2616,1144,2280,1808,1440,1832);
makePolygon(3160,728,4592,1496,3904,1936,3160,1512);
makePolygon(504,3512,1848,2792,1728,3584,1136,3968);
makePolygon(2584,2616,3712,3720,3048,3976,2440,3456);
makePolygon(1672,4344,1768,5912,1128,5544,1064,4872);
makePolygon(3272,4640,4440,5752,3768,5992,3096,5392);
UL-UR-ML-MR-BL-BR
'''
plates = {'UL':'WT_MM','UR':'WT_SFM','ML':'OP1839_MM','MR':'OP1839_SFM','BL':'DL1839_MM','BR':'DL1839_SFM'}
results = {plates['UL']:[], plates['UR']:[], plates['ML']:[], plates['MR']:[], plates['BL']:[], plates['BR']:[]}

alltxt = macro_text.split(';')
count = macro_text.count('makePolygon')
allnumtxt = []
for i in range(count):
	a = alltxt[i].find('(') + 1
	b = alltxt[i].find(')')
	allnumtxt.append(map(int, alltxt[i][a:b].split(',')))
		
print(allnumtxt)
# Make a header based on the measurment
header = 'time\t%s\t%s\t%s\t%s\t%s\t%s\n'%(plates['UL'],plates['UR'],plates['ML'],plates['MR'],plates['BL'],plates['BR'])

# Make a temp directory for data storage temporary data in case of failier
try:
	os.mkdir('%s/temp'%target_path)
except OSError as e:
	if e.errno == 17:
		print('"temp" directory already existed!')
	else:
		print('WTF???')
		exit('WTF???')

# Start measuring	
for i in range(max_img_num):

	# Open file
	path = "%s/img_%s_cropped.jpg"%(working_path, str(i+1).zfill(3))
	print("Measuring: " + path)
	imp = IJ.openImage(path)
	imp.show()

	# Make shape and measure, looping for sample number
	for a in range(count):
		num_positions = len(allnumtxt[a])
		xs = tuple(allnumtxt[a][x] for x in range(0, num_positions, 2))
		ys = tuple(allnumtxt[a][x] for x in range(1, num_positions, 2))
		imp.setRoi(ij.gui.PolygonRoi(xs, ys, len(xs), ij.gui.Roi.POLYGON))
		IJ.run("Measure")
	imp.close() # Clean playground

	# Write Measurement to temp file
	temp_path = "%s/temp/temp_%i.txt"%(target_path,i+1)
	IJ.saveAs("Results", temp_path)
	# Read from temp file, put the result in "content"
	foo = open(temp_path, 'rb')
	content = list(csv.reader(foo, delimiter='\t'))
	foo.close()
	
	# Deal different output from IJ.saveAs function by
	# Judge the first row and build different indexing number
	if len(content[0]) == 2: 
		# If output contains header and numbered
		a = list(range(1,7))
		b = 1
	else: # If output is simple
		a = list(range(0,6))
		b = 0
	
	# Put result of single picture measurment in "results" dictionary
	results[plates['UL']].append(content[a[0]][b])
	results[plates['UR']].append(content[a[1]][b])
	results[plates['ML']].append(content[a[2]][b])
	results[plates['MR']].append(content[a[3]][b])
	results[plates['BL']].append(content[a[4]][b])
	results[plates['BR']].append(content[a[5]][b])
	# Generate resulting string and append to temp
	temp_string = '%s\t%s\t%s\t%s\t%s\t%s\t%s\n'%(str(i+1).zfill(3),
									 		 results[plates['UL']][i], 
									 		 results[plates['UR']][i], 
									 		 results[plates['ML']][i], 
									 		 results[plates['MR']][i],
									 		 results[plates['BL']][i], 
									 		 results[plates['BR']][i])
	temp = open("%s/temp/temp.txt"%target_path, 'a')
	if i == 0:
		temp.write('\n%s\n'%strftime('%X %d/%m/%Y %Z'))
		temp.write(header)
		temp.write(temp_string)
	else:
		temp.write(temp_string)
	temp.close()
	IJ.run("Clear Results")
#	if i == 1:
#		break

# Put all results in a file
output = open('%s/%s_confluent_plates.txt'%(target_path, path_name), 'w')
output.write(header)

for i in range(max_img_num):
	string = '%s\t%s\t%s\t%s\t%s\t%s\t%s\n'%(str(i+1).zfill(3),
									 		 results[plates['UL']][i], 
									 		 results[plates['UR']][i], 
									 		 results[plates['ML']][i], 
									 		 results[plates['MR']][i],
									 		 results[plates['BL']][i], 
									 		 results[plates['BR']][i])
	output.write(string)
#	if i == 1:
#		break
output.close() 



