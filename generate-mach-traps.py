#!/usr/bin/env python

import os
import sys
import string
import datetime
import json

# Generating list of MACH traps
# [number, return type, name, number of args, number of 32bit words (related to munger), args...n, munger, source]
def mach_list_generate():
	print "[+] Generating mach-traps list data structure"
	mach_traps = []

	# Opening up the declaration file for MACH traps and performing parsing voodoo
	with open(PATH_MACH_TRAPS, "r+b") as fd:
		for line in fd.readlines():
			entry = []
			line = line.strip()

			if line.find("\tMACH_TRAP(") != -1:
				elems = line.split()
				entry.append(elems[1])
				entry.append(elems[3].replace("MACH_TRAP(", '').replace(',', ''))
				entry.append(elems[4].replace(',', ''))
				entry.append(elems[5].replace(',', ''))
				entry.append(elems[6].replace("),", ''))
				mach_traps.append(entry)

	'''
	for el in mach_traps:
		print el
	'''

	print "\tdone"

	return mach_traps

# This comes in handy when generating HTML output
def determine_highest_num_args():

	highest_num = 0
	for el in mach_traps_list:
		if(int(el[2]) > highest_num):
			highest_num = int(el[2])

	print "[+] Highest # of args is " + str(highest_num)

	return highest_num

# Return types of MACH traps can be pull out from xnu/osfmk/mach/mach_traps.h
def determine_trap_rettype():
	print "[+] Pulling out return types for each trap"

	with open(PATH_MACH_TRAPS_ARGS, "r+b") as fd:
		for i, elem in enumerate(mach_traps_list):

			#print '\n' + elem[1]

			for line in fd.readlines():
				line = line.strip()

				if line.find(elem[1]+'(') != -1:
					line = line.split(' ')

					# little heuristics because they screw-up with new-lines
					# e.g. line for iokit_user_client_trap has only 2 elemes (_all_ others have 3!)
					if line[1].replace('(', '') == elem[1]:
						arg = line[0]
						#print '\t' + line[0] + ' ' + line[1]
					else:
						arg = line[1]
						#print '\t' + line[1] + ' ' + line[2]

					mach_traps_list[i].insert(1, arg)

			fd.seek(0)

	'''
	for el in mach_traps_list:
		print el
	'''

	print "\tdone"

# Arguments for MACH traps are in xnu/osfmk/mach/mach_traps.h
# Lots of applied heuristics. Lawl.
# Probably won't work if anything changes
def determine_trap_args():
	print "[+] Enumerating arguments for each trap"

	# Reading-in file line by line for further processing
	mach_traps_args = []

	with open(PATH_MACH_TRAPS_ARGS, "r+b") as fd:
		for line in fd.readlines():
			line = line.strip()
			mach_traps_args.append(line)

	for i, elem in enumerate(mach_traps_list):

		if elem[2] == "kern_invalid":
			continue

		lim = int(elem[3])
		#print elem[2] + " # args = " + str(lim)

		# If traps take no arguments then we can skip it
		if lim == 0:
			continue

		for j, line in enumerate(mach_traps_args):
			if line.find(elem[2] + '(') != -1 or line.find(elem[2] + "_args {") != -1:

				# Heuristics for usless lines like "<syscall>(void)" etc
				if line.find(')') != -1:
					continue

				# Heuristics for weeding out "struct <syscall> *args" lines
				if mach_traps_args[j+1].find("*args") != -1:
					continue

				#print '\t' + line
				#print '\t\t' + mach_traps_args[j+1]

				for k in range(lim):
					arg = mach_traps_args[j+k+1]

					arg = arg.replace("PAD_ARG_(", '')

					# Funny heuristics for situation where we have blank PAD_ARG_8 in iokit_user_client_trap
					if arg.find("PAD_ARG") != -1:
						arg = mach_traps_args[j+k+2]

					arg = arg.replace("PAD_ARG_(", '')
					arg = arg.replace(',', '')
					arg = arg.replace(');', '')

					#print '\t\t' + arg

					# k+5 since we're starting from 5th field of N-th record in mach_traps_list list
					mach_traps_list[i].insert(k+5, arg)


				# This break is ingenious. Some traps have both extern and struct with arguments
				# So we're dealing with it here, since either struct or extern suffices for our
				# purposes; after we pull out arguments from either one we are breaking!
				break

	'''
	for el in mach_traps_list:
		print el
	'''

	print "\tdone"

def make_traps_file_xrefs():
	print "[+] Generating tags file for " + PATH_XNU_SOURCE

	# Stage 0: Generate tags for XNU source
	cmd = PATH_EXUBERANT_CTAGS + " -R " + PATH_XNU_SOURCE
	os.system(cmd)
	print "\tdone"

	# Mine for impl files
	print "[+] Mining for implementation files in tags file"
	for i, trap in enumerate(mach_traps_list):
		fd = open("tags", "r+b")
		for line in fd.readlines():
			line = line.strip()
			cols = line.split()
			if trap[2] == cols[0]:
				if line.find(".h") != -1:
					continue

				#print trap[2]
				#print '\t' + cols[1]

				mach_traps_list[i].append(cols[1].replace(PATH_XNU_SOURCE, URL_XNU_SOURCE))

	'''
	for el in mach_traps_list:
		print el
	'''

	print "\tdone"

def generate_json():
	print "[+] Generating JSON file..."

	with open(OUTPUT_JSON, 'w') as fd:
		json.dump(mach_traps_list, fd, indent=4)

	print "\tdone"

def generate_html():
	print "[+] Generating HTML output..."

	html = '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="description" content="macOS (xnu) MACH traps reference table.">
    <meta name="keywords" content="Apple, macOS, OS X, OSX, XNU, MACH, traps, system calls, OS internals, reference, low level, programming, c, c++, assembler, kernel, reverse engineering, malware analysis">
    <meta name="author" content="Andrzej Dyjak, dyjakan">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>macOS MACH Traps</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-alpha.6/css/bootstrap.min.css" integrity="sha384-rwoIResjU2yc3z8GV/NPeZWAv56rSmLldC3R/AZzGRnGxQQKnKkoFVhFQhNUwEyJ" crossorigin="anonymous">
  </head>
  <body>
'''

	html += "<div class=\"container-fluid\">\n"
	html += BANNER
	html += "\t<table class=\"table table-sm table-hover\">\n"

	html += "\t<thead class=\"thead-inverse\">\n"
	html += "\t\t<tr>\n"
	html += "\t\t\t<th>" + "#" + "</th>\n"
	html += "\t\t\t<th>" + "Name" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#1" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#2" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#3" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#4" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#5" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#6" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#7" + "</th>\n"
	html += "\t\t\t<th>" + "Arg#8" + "</th>\n"
	html += "\t\t\t<th>" + "Munger" + "</th>\n"
	html += "\t\t\t<th>" + "Implementation" + "</th>\n"
	html += "\t\t</tr>\n"
	html += "\t</thead>\n"

	for trap in mach_traps_list:

		html += "\t<tr>\n"

		html += "\t\t<td>" + trap[0] + "</td>\n"
		html += "\t\t<td>" + trap[1] + " <b>" + trap[2].replace('_trap', '') + "</b></td>\n"

		delta = highest_num_args - int(trap[3])

		# Dealing with 'kern_invalid'
		if trap[5] == "NULL":
			for i in range(highest_num_args):
				html += "\t\t<td>-</td>\n"

			# This is for blank munger
			html += "\t\t<td>-</td>\n"

			html += "\t\t<td><a href=\"" + trap[6] + "\">" + trap[6].replace(URL_XNU_SOURCE, '') + "</a></td>\n"

			html += "\t</tr>\n"
			continue

		# Adding each argument of the trap into html
		for i in range(int(trap[3])):
			html += "\t\t<td>" + trap[5+i] + "</td>\n"

		# Filling-up left space from unused arguments
		for i in range(delta):
			html += "\t\t<td>-</td>\n"

		# Adding a munger; this funny heuristics is for "thread_switch" trap
		# Which apparently has 2 implementation files, hence 2 links :<
		if trap[-2].find("http") != -1:
			html += "\t\t<td>" + trap[-3] + "</td>\n"
		else:
			html += "\t\t<td>" + trap[-2] + "</td>\n"

		# Adding a link to implementation file
		html += "\t\t<td><a href=\"" + trap[-1] + "\">" + trap[-1].replace(URL_XNU_SOURCE, '') + "</a></td>\n"

		html += "\t</tr>\n"

	html += "\t</table>\n"
	html += "</div>"
	html += '''
    <script src="https://code.jquery.com/jquery-3.1.1.slim.min.js" integrity="sha384-A7FZj7v+d/sdmMqp/nOQwliLvUsJfDHW+k9Omg/a/EheAdgtzNs3hpfag6Ed950n" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/tether/1.4.0/js/tether.min.js" integrity="sha384-DztdAPBWPRXSA/3eYEEUWrWCy7G5KFbe8fFjk5JAIxUYHKkDx6Qin1DkWx51bBrb" crossorigin="anonymous"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-alpha.6/js/bootstrap.min.js" integrity="sha384-vBWWzlZJ8ea9aCX4pEW3rVHjgjt7zpkNpZk+02D9phzyeVkE+jo0ieGizqPLForn" crossorigin="anonymous"></script>
  </body>
</html>
'''

	with open(OUTPUT_HTML, 'w') as fd:
		fd.write(html)

	print "\tdone"


def main():
	# Kung-foo for MACH traps
	global mach_traps_list
	mach_traps_list = mach_list_generate()

	# Find what is the highest number of arguments
	global highest_num_args
	highest_num_args = determine_highest_num_args();

	# Find the return type of each trap
	determine_trap_rettype()

	# Find all arguments for each trap
	determine_trap_args()

	# Find implementation file for each trap in XNU source
	make_traps_file_xrefs()

	# Dump mach_traps_list as JSON
	generate_json()

	# yayks!
	generate_html()

	print "[+] Great success!"

if __name__ == "__main__":
	if(len(sys.argv) < 2):
		print sys.argv[0] + " <XNU source path/>"
		sys.exit(1)

	PATH_XNU_SOURCE = sys.argv[1]
	URL_XNU_SOURCE = "https://opensource.apple.com/source/xnu/xnu-4570.1.46/"
	PATH_EXUBERANT_CTAGS = "/usr/local/Cellar/ctags/5.8_1/bin/ctags"
	PATH_MACH_TRAPS = PATH_XNU_SOURCE + "osfmk/kern/syscall_sw.c"
	PATH_MACH_TRAPS_ARGS = PATH_XNU_SOURCE + "osfmk/mach/mach_traps.h"
	OUTPUT_JSON = "osx-mach-traps.json"
	OUTPUT_HTML = "osx-mach-traps.html"

	# mention: timestamp, original list from XNU sources, name/handle/email
	BANNER = "<h1>macOS MACH Traps</h1>\n"
	v1 = PATH_XNU_SOURCE[PATH_XNU_SOURCE.find("xnu-"):]
	ts = datetime.datetime.now().strftime("%A, %d %B %Y")
	twitter = "<a href=\"https://twitter.com/andrzejdyjak\">@andrzejdyjak</a>"
	BANNER += "<p>Generated from <i><a href=\"" + URL_XNU_SOURCE + "\">" + v1.upper() + "</a></i> on <i>" + ts + "</i> by " + twitter + ".</p>\n"
	BANNER += "<p>Description for <a href=\"osx-mach-traps.json\">JSON dump</a> elements:</p>"
	BANNER += "<pre>[\n\ttrap number,\n\treturn type,\n\ttrap name,\n\tnumber of args,\n\thow wide argument structure is (in 32-bit words; it's related to munger),\n\targ 1, ..., arg n,\n\tmunger,\n\tsource\n]</pre>"
	BANNER += "<p>You can find github repository <a href=\"https://github.com/dyjakan/osx-syscalls-list\">here</a>. Feedback, ideas, bugs, <i>et cetera</i> &#8211; <a href=\"https://sigsegv.pl\">give me a shout</a>.</p>\n"

	main()
