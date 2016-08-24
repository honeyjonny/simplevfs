
import argparse

class Command(object):
	def __init__(self, args):
		print(args)
		pass

	def execute(self):
		print("here")
		pass

class ListCommand(object):
	"""Incapsulates list command logic"""
	def __init__(self, args):
		pass

	def execute(self):
		print("list command")
		pass
		

class AddFolderCommand(object):
	"""Incapsulates add folder command logic"""
	def __init__(self, args):
		self.path = args.path
		self.foldername = args.foldername

	def execute(self):
		print("add_folder")
		pass

class AddFileCommnad(object):
	"""Incapsulated AddFileCommnad logic"""
	def __init__(self, args):
		self.path = args.path
		self.filename = args.filename
		self.content = args.content

	def execute(self):
		print("add file command")
		pass

class RemoveAnyCommand(object):
	"""Incapsulates RemoveAnyCommand logic"""
	def __init__(self, args):
		self.path = args.path

	def execute(self):
		print("remove_any command")
		pass
		
class ShowFileCommand(object):
	"""Incapsulates ShowFileCommand logic"""
	def __init__(self, args):
		self.path = args.path

	def execute(self):
		print("show file command")
		pass
		
class EditCommand(object):
	"""Incapsulates EditCommand logic"""
	def __init__(self, args):
		self.path = args.path
		self.newname = args.name or None
		self.newcontent = args.content or None

	def execute(self):
		print("edit command")
		pass
		

def parseArgs():
	"""Creates options and parsers for different command line arguments"""

	parser = argparse.ArgumentParser(description="Simple virtual file system app")

	subparsers = parser.add_subparsers(help="list of available commands\n")

	list_command = subparsers.add_parser("list", help="list all file system hierarhy")
	list_command.set_defaults(func=ListCommand)

	add_folder = subparsers.add_parser("add_folder", help="add folder into specifed folder")
	add_folder.add_argument("path", nargs=1, help="path, like Root/My/Folder")
	add_folder.add_argument("foldername", nargs=1, help="new folder name")
	add_folder.set_defaults(func=AddFolderCommand)

	add_file = subparsers.add_parser("add_file", help="add file in specific folder with defined content")
	add_file.add_argument("path", nargs=1, help="path, like Root/My/Folder")
	add_file.add_argument("filename", nargs=1, help="new file name")
	add_file.add_argument("content", nargs=1, help="content of new file")
	add_file.set_defaults(func=AddFileCommnad)

	remove_any = subparsers.add_parser("remove", help="remove file or folder at specified path")
	remove_any.add_argument("path", nargs=1, help="path to removed file|folder")
	remove_any.set_defaults(func=RemoveAnyCommand)

	show_parser = subparsers.add_parser("show", help="show content of file at specified path")
	show_parser.add_argument("path", nargs=1, help="path to file to show, like: Root/My/Folder/MyFile.txt")
	show_parser.set_defaults(func=ShowFileCommand)

	edit_parser = subparsers.add_parser("edit", help="edit folder|file name on specified path | file name + file content")
	edit_parser.add_argument("path", nargs=1, help="path to file|folder")
	edit_parser.add_argument("--name", nargs=1, help="optionally argument for new name of file|folder", default=None)
	edit_parser.add_argument("--content", nargs=1, help="optionally argument for new file content"
		"(work only if path argument specified on a file)", default=None)
	edit_parser.set_defaults(func=EditCommand)


	args = parser.parse_args()

	if hasattr(args, "func"):
		commandInstance = args.func(args)
		commandInstance.execute()
	else:
		parser.print_help()

def main():
	parseArgs()

if __name__ == '__main__':
	main()