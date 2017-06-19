from ij import IJ
import csv
import os
from time import strftime

# Take care of total path and numbers!!!!!!!
working_path = 'F:/20170612_sco1839'
max_img_num = 98
path_name = working_path.split('/')[-1]
target_path = 'd:/WORKs/Project_Sporulation/Pictures/%s_scanner'%path_name

os.chdir(working_path)
print("Working at: %s"%os.getcwd())
print("Target dir: %s"%target_path)


IJ.run("Set Measurements...", "mean redirect=None decimal=4")
IJ.run("Clear Results")


#
## change file name
#for i in range(1,max_img_num+1):
#	try:
#		filename = 'im_%s.jpg'%str(i).zfill(2)
#		newname = 'img_%s.jpg'%str(i).zfill(3)
#		os.rename(filename, newname)
#	except:
#		print('img_%s.jpg is not in the folder'%str(i).zfill(2))
#		break


# Get positions for measurment into a list of 4 number lists
macro_text = '''
makeOval(1072, 984, 1568, 1568);
makeOval(3216, 960, 1568, 1568);
makeOval(360, 3008, 1568, 1568);
makeOval(2536, 2976, 1568, 1568);
makeOval(1056, 5072, 1568, 1568);
makeOval(3168, 5048, 1568, 1568);
op8-wt2-del-del-cm-wt2
'''
plates = {'UL':'OP1839CR8','UR':'WT_1','ML':'KO1839_1','MR':'KO1839_2','BL':'CM1839','BR':'WT_2'}
results = {plates['UL']:[], plates['UR']:[], plates['ML']:[], plates['MR']:[], plates['BL']:[], plates['BR']:[]}

alltxt = macro_text.split(';')
count = macro_text.count('makeOval')
allnumtxt = []
for i in range(count):
	a = alltxt[i].find('(') + 1
	b = alltxt[i].find(')')
	allnumtxt.append(map(int, alltxt[i][a:b].split(', ')))
	
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
	path = "%s/img_%s.jpg"%(working_path, str(i+1).zfill(3))
	print("Measuring: " + path)
	imp = IJ.openImage(path)
	imp.show()
	for a in range(count):
		IJ.makeOval(*allnumtxt[a])
		IJ.run("Measure")
	imp.close()
	temp_path = "%s/temp/temp_%i.txt"%(target_path,i+1)
	IJ.saveAs("Results", temp_path)
	foo = open(temp_path, 'rb')
	content = list(csv.reader(foo, delimiter='\t'))
	foo.close()
	if len(content[0]) == 2:
		a = list(range(1,7))
		b = 1
	else:
		a = list(range(0,6))
		b = 0
	results[plates['UL']].append(content[a[0]][b])
	results[plates['UR']].append(content[a[1]][b])
	results[plates['ML']].append(content[a[2]][b])
	results[plates['MR']].append(content[a[3]][b])
	results[plates['BL']].append(content[a[4]][b])
	results[plates['BR']].append(content[a[5]][b])
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



