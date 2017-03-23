#!/usr/bin/env python

import os
import sys
import shutil
import string
import datetime
import json


# Make a temporary file of BSD syscalls without any additional shit around
def make_temp_bsd():
	print "[+] Making temporary system call list in " + PATH_BSD_TEMP_FILE
	fdin = open(PATH_BSD_SYSCALLS, "r+b")
	fdout = open(PATH_BSD_TEMP_FILE, "w+b")

	data = fdin.read()
	data = data[data.find("0\t"):]  # hacky way to set data ptr to proper field
									# since first syscall is prepended with '0\t'
	fdout.write(data)

	fdout.close()
	fdin.close()
	print "\tdone"

# Generating BSD system call list as a data structure
# [number, return type, name, number of args, arg...n, source]
def bsd_list_generate():
	print "[+] Generating system call matrix data structure"
	fdin = open(PATH_BSD_TEMP_FILE, "r+b")
	data = fdin.read()
	fdin.close()

	# Split data by lines
	data = string.split(data, '\n')

	# Remove all empty lines
	for i, line in enumerate(data):
		if not line:
			data.pop(i)

	# Remove all asm comments ';'
	tmp = []
	for i, line in enumerate(data):
		if i == 0 or not line.startswith(';'):
			tmp.append(line)
	data = tmp

	# Crafting syscall table (as 2 dimensional matrix)
	syscall_matrix = []
	for line in data:
		entry = []

		if line.startswith("#"):
			# Apple shitheads are lousy.
			if line.find("#endif") != -1:
				entry.append("#endif")
				syscall_matrix.append(entry)
				continue

			entry.append(line)
			syscall_matrix.append(entry)
			continue

		line = line.replace(" (", "(")
		elems = line.split()

		# Syscall ID
		entry.append(elems[0])

		# Syscall return type
		entry.append(elems[4])

		# Syscall name
		entry.append(elems[5][0:elems[5].find('(')])

		# Enumerating arguments of the syscall
		# This shit is kinda tricky. For couple of reasons: 1) There _are_
		# corner cases (e.g. no args), 2) Unknown # of args per syscall, 3)
		# argument can be more than a tuple e.g. 'struct name arg'
		#
		i = 5
		argnum = 0 # we will use it to count number of args
		arg = "" # we're using it to create each arg
		tmp = [] # temporary list of args for each syscall
		while True:
			# Corner case where syscall takes 0 args (denoted "void")
			if(elems[6] == '}' or elems[6] == "NO_SYSCALL_STUB;"):
				entry.append(str(argnum))
				break
			# If argnum > 0 then it's our first iteration always
			elif(i == 5):
				arg = elems[i][elems[i].find('(')+1:]
				i += 1
				continue
			elif(elems[i] != '}' and elems[i] != "NO_SYSCALL_STUB;"):
				if(elems[i].find(')') != -1):
					arg += ' '+elems[i][:elems[i].find(')')]
					tmp.append(arg)
					argnum += 1
					entry.append(str(argnum))
					break
				if(elems[i].find(',') == -1):
					arg += ' '+elems[i]
					i += 1
					continue
				else:
					arg += ' '+elems[i][:elems[i].find(',')]
					tmp.append(arg)
					argnum += 1
					arg = ""
					i += 1

			else:
				break

		# We're adding args from our temporary list
		for el in tmp:
			entry.append(el)

		# Strip prepended spaces from syscall's args
		for i, elem in enumerate(entry):
			entry[i] = elem.strip()

		syscall_matrix.append(entry)

	'''
	for entry in syscall_matrix:
		print entry
	sys.exit()
	'''

	# Clean-up
	cmd = "rm " + PATH_BSD_TEMP_FILE
	os.system(cmd)

	print "\tdone"
	return syscall_matrix

# This comes in handy when generating HTML output
def determine_highest_num_args():

	highest_num = 0
	for el in bsd_syscall_list:
		if el[0].startswith('#'):
			continue
		if(el[3] > highest_num):
			highest_num = el[3]

	print "[+] Highest # of args is " + highest_num

	return highest_num

def make_syscall_file_xrefs():
	print "[+] Generating tags file for " + PATH_XNU_SOURCE
	# Stage 0: Generate tags for XNU source
	cmd = PATH_EXUBERANT_CTAGS + " -R " + PATH_XNU_SOURCE
	os.system(cmd)
	print "\tdone"

	# Stage 1: Mine for impl files!
	print "[+] Mining for implementation files in tags file"
	for i, syscall in enumerate(bsd_syscall_list):
		if syscall[0].startswith('#'):
			continue

		# Technically, we could skip them. They ain't do notin'. So we do.
		# However, since there are quite static throughout releases we can still
		# add them into final output when generating HTML
		#elif syscall[2] == "nosys":
		#    continue
		#elif syscall[2] == "enosys":
		#    continue

		else:
			fd = open("tags", "r+b")
			for line in fd.readlines():
				line = line.strip()
				#if line.find("struct "+syscall[2]+"_args") != -1:
				cols = line.split()
				if syscall[2] == cols[0]:
					if line.find(".h") != -1:
						continue

					# LOL, it's pointless since cols are already splitted
					# hence we can print cols[1] and have the same result
					# look at solution for MACH traps ;)
					data = string.split(line, '\t')
					#print syscall[2] + ": " + data[0] + " " + data[1]
					bsd_syscall_list[i].append(data[1].replace(PATH_XNU_SOURCE, URL_XNU_SOURCE))

	'''
	for elem in bsd_syscall_list:
		print elem
	'''

	print "\tdone"

def generate_json():
	print "[+] Generating JSON file..."

	with open(OUTPUT_JSON, 'w') as fd:
		json.dump(bsd_syscall_list, fd, indent=4)

	print "\tdone"

def generate_html():
	print "[+] Generating HTML output..."

	html = '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="description" content="macOS (xnu) BSD system calls reference table.">
    <meta name="keywords" content="Apple, macOS, OS X, OSX, XNU, BSD, system calls, OS internals, reference, low level, programming, c, c++, assembler, kernel, reverse engineering, malware analysis">
    <meta name="author" content="Andrzej Dyjak, dyjakan">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>macOS BSD System Calls</title>
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
	html += "\t\t\t<th>" + "RDI" + "</th>\n"
	html += "\t\t\t<th>" + "RSI" + "</th>\n"
	html += "\t\t\t<th>" + "RDX" + "</th>\n"
	html += "\t\t\t<th>" + "RCX" + "</th>\n"
	html += "\t\t\t<th>" + "R8" + "</th>\n"
	html += "\t\t\t<th>" + "R9" + "</th>\n"
	html += "\t\t\t<th>" + "Stack" + "</th>\n"
	html += "\t\t\t<th>" + "Stack" + "</th>\n"
	html += "\t\t\t<th>" + "Implementation" + "</th>\n"
	html += "\t\t</tr>\n"
	html += "\t</thead>\n"

	for elem in bsd_syscall_list:

		# Corner case where we have #define
		# The loop takes care of blank cells in the table
		if elem[0].startswith('#'):
			html += "\t<tr class=\"table-info\">\n"
			html += "\t\t<td>" + elem[0] + "</td>\n"

			# Result of this loop is connected with try/except later; remember!
			for i in range(highest_num_args+2):
				html += "\t\t<td></td>\n"

			html += "\t</tr>\n"
			continue

		html += "\t<tr>\n"

		html += "\t\t<td>" + elem[0] + "</td>\n"
		html += "\t\t<td>" + elem[1] + " <b>" + elem[2] + "</b></td>\n"

		delta = highest_num_args - int(elem[3])

		# Filling up, dynamically, arguments of a syscall
		if(int(elem[3]) == 0):
			for i in range(delta):
				html += "\t\t<td>-</td>\n"
		else:
			for i in range(int(elem[3])):
				html += "\t\t<td>" + elem[4+i] + "</td>\n"

			for i in range(delta):
				html += "\t\t<td>-</td>\n"

		# Heuristics for pulling out implementation file, lawl
		try:
			link = elem[3+int(elem[3])+1]
			html += "\t\t<td><a href=\"" + link + "\">" + link.replace(URL_XNU_SOURCE, '') + "</a></td>\n"
		except:
			html += "\t\t<td></td>\n"
			html += "\t</tr>\n"
			continue

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
	# Kung-foo for BSD syscalls
	# bsd_syscall_list contains not only syscalls but also #defines!
	make_temp_bsd()
	global bsd_syscall_list
	bsd_syscall_list = bsd_list_generate()

	# Find what is the highest number of arguments
	# Lawl, but it's actually _pretty_ handy!
	global highest_num_args
	highest_num_args = determine_highest_num_args();
	highest_num_args = int(highest_num_args)

	# Kung-foo for implementation files xrefs
	make_syscall_file_xrefs()

	# Dump bsd_syscall_list as JSON
	generate_json()

	# yayks!
	generate_html()

	print "[+] Great success!"

if __name__ == "__main__":
	if(len(sys.argv) < 2):
		print sys.argv[0] + " <XNU source path/>"
		sys.exit(1)

	PATH_XNU_SOURCE = sys.argv[1]
	URL_XNU_SOURCE = "https://opensource.apple.com/source/xnu/xnu-3789.41.3/"
	PATH_EXUBERANT_CTAGS = "/usr/local/Cellar/ctags/5.8_1/bin/ctags"
	PATH_BSD_SYSCALLS = PATH_XNU_SOURCE + "bsd/kern/syscalls.master"
	PATH_BSD_TEMP_FILE = "/tmp/bsd-syscall-tmp"
	OUTPUT_JSON = "osx-bsd-syscalls.json"
	OUTPUT_HTML = "osx-bsd-syscalls.html"

	# mention: timestamp, original list from XNU sources, name/handle/email
	BANNER = "<h1>macOS BSD System Calls</h1>\n"
	v1 = PATH_XNU_SOURCE[PATH_XNU_SOURCE.find("xnu-"):]
	ts = datetime.datetime.now().strftime("%A, %d %B %Y")
	github = "<a href=\"https://github.com/dyjakan\">@dyjakan</a>"
	BANNER += "<p>Generated from <i><a href=\"" + URL_XNU_SOURCE + "\">" + v1.upper() + "</a></i> on <i>" + ts + "</i> by " + github + ".</p>\n"
	BANNER += "<p>Description for <a href=\"osx-bsd-syscalls.json\">JSON dump</a> elements (apart from <i>conditionals</i>):</p>"
	BANNER += "<pre>[\n\tsyscall number,\n\treturn type,\n\tsyscall name,\n\tnumber of args,\n\targ 1, ..., arg n,\n\tsource\n]</pre>"
	BANNER += "<p>You can find github repository <a href=\"https://github.com/dyjakan/osx-syscalls-list\">here</a>. Feedback, ideas, bugs, <i>et cetera</i> &#8211; <a href=\"https://sigsegv.pl\">give me a shout</a>.</p>\n"

	main()
