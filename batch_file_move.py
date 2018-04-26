import os
def movefiles(target, ext, makedir):
	# target in *_* format
	# ext in '.tif' format
	# makedir in true or false format
	dirfiles = os.listdir(setdir)
	files = []
	for file in dirfiles:
		if file.endswith(target + ext):
			files.append(file)
	if makedir:
		os.mkdir(setdir + '/' + target)
	for i in range(5):
		print(files[i])
	for file in files:
		os.rename(setdir + '/' + file, setdir + '/' + target + '/' + file)
def movetargets():
	for target in targets:
		movefiles(target,'.tif',False)
def removetargets(setdir,targets):
	for target in targets: 
		for i in range(117,155):
			os.remove(setdir + '/' + target + '/' + 'solidgrowth_{}_{}_{}.tif'.format(i,targetdir,target))
def renamefile(setdir):
	for root, dirs, files in os.walk(setdir):
		for file in files:
			if file.endswith('.jpg'):
				path = os.path.join(root, file)
				print(path)
			#for i in range(20,155):
			#	os.rename(path + 'solidgrowth_{}_{}_{}.tif'.format(str(i), targetdir, target), path + 'solidgrowth_{}_{}_{}.tif'.format(str(i).zfill(3), targetdir, target))  
			#break
		#break

#targets = ['1_1','2_1','2_2','3_1','3_2','3_3','4_1','4_2','5_1']
targets = ['2_JA', '2_MM', '3_JA', '3_MM']
targetdir = 'row_2_JA'
setdir = 'JASvs_QL109_2.slices/plates' 

#removetargets('JASvs.QL109.slices/plates/{}'.format(targetdir),targets)
#movetargets()
#renamefile(setdir)
for target in targets:
	movefiles(target,'.tif',True)
