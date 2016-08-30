
import argparse
import os
import sqlite3

from enum import Enum

CREATE_TABLE_FOLDERS = """
CREATE TABLE IF NOT EXISTS 
Folders (id integer PRIMARY KEY AUTOINCREMENT, foldername text NOT NULL UNIQUE)"""

CREATE_TABLE_FOLDERS_HIERACHY = """
CREATE TABLE IF NOT EXISTS
FoldersTree (parent_id integer NOT NULL, child_id integer NOT NULL, path_len integer NOT NULL,
PRIMARY KEY (parent_id, child_id),
FOREIGN KEY (parent_id) REFERENCES Folders(id),
FOREIGN KEY (child_id) REFERENCES Folders(id))
"""

CREATE_TABLE_FILES = """
CREATE TABLE IF NOT EXISTS 
Files (id integer PRIMARY KEY AUTOINCREMENT, folder_id integer NOT NULL, 
filename text NOT NULL, content text DEFAULT '', size integer DEFAULT 0, 
CONSTRAINT ParentFolder FOREIGN KEY (folder_id) REFERENCES Folders(id) ON DELETE CASCADE)"""

CREATE_ROOT_FOLDER = """INSERT INTO Folders (foldername) VALUES ('Root')"""

class DatabaseProvider(object):
	DatabaseFile = "database.sqlite"

	@staticmethod
	def openConnection():
		return sqlite3.connect(DatabaseProvider.DatabaseFile)

	def __init__(self):
		self.conn = DatabaseProvider.openConnection()

	def __enter__(self):
		return self.conn

	def __exit__(self, extype, exvalue, exdebug):
		if extype is None:
			self.conn.close()
		else:
			self.conn.close()
			print("Exeption: ", extype)
			return False

class OpenDbTransaction(object):
	def __init__(self, dbconn):
		self.conn = dbconn

	def __enter__(self):
		return self.conn.cursor()

	def __exit__(self, extype, exvalue, exdebug):
		if extype is None:
			self.conn.commit()
		else:
			self.conn.rollback()
			print("Exeption: ", extype)
			return False

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
		#print("list command")
		with DatabaseProvider() as conn:
			# for row in conn.execute("SELECT * FROM Folders"):
			# 	print(row)
			# print("------------------------------------------")
			# for row in conn.execute("SELECT * FROM FoldersTree"):
			# 	print(row)
			# print("*******************************************")

			folderDepth = 1
			rootFolder = conn.execute("""
				SELECT id, foldername 
				FROM Folders 
				WHERE foldername = 'Root'""").fetchone()
			#print(rootFolder)
			self.printFolderStructure(folderDepth, rootFolder, conn)


	def printFolderStructure(self, folderDepth, folderRow, dbConn):

		self.printEntity(folderDepth, folderRow[1])		

		self.printFilesInFolder(folderDepth, folderRow, dbConn)

		folderDepth += 1

		for folderRow in dbConn.execute("""
			SELECT id, foldername 
			FROM Folders as fold 
			JOIN FoldersTree as tree 
			ON (fold.id = tree.child_id) 
			WHERE tree.parent_id = %d""" % folderRow[0]).fetchall():
			self.printFolderStructure(folderDepth, folderRow, dbConn)

	def printFilesInFolder(self, folderDepth, folderRow, dbConn):

		for file in dbConn.execute("""
			SELECT filename, size 
			FROM Files as files 
			WHERE files.folder_id = %d""" % folderRow[0]).fetchall():
			self.printEntity(folderDepth + 1, file[0], file[1])

	def printEntity(self, depth, entityName, size = None):

		signs = '-' * depth

		if size is not None:
			print("%s %s  size: %d" % (signs, entityName, size))
		else:
			print("%s %s" % (signs, entityName))

class EntityType(Enum):
	"""Enumerate types of entities for DeleteAnyCommand"""	
	Folder = 1
	File = 2
		
class CommonDataQueriesMixin(object):
	"""Mix-ins into command class for reuse of db acces code"""

	def findParentFolderByNameAndPathLen(self, parentFolderName, pathLen, dbConn):

		parentFolderRow = None

		if pathLen == 0:

			parentFolderRow = dbConn.execute("SELECT id, foldername FROM Folders WHERE foldername = 'Root'").fetchone()

		else:

			findParentFolder = """
			SELECT id, foldername 
			FROM Folders as fold 
			JOIN FoldersTree as tree ON (fold.id = tree.child_id) 
			WHERE fold.id = (SELECT id FROM Folders WHERE foldername = '%s')
			AND tree.path_len = %d""" % (parentFolderName, pathLen)

			parentFolderRow = dbConn.execute(findParentFolder).fetchone()

		return parentFolderRow

	def clearString(self, pathString):
		return pathString.lstrip("/").rstrip("/").replace('"',"").replace("'","")

	def getPathList(self, fullPath):
		return self.clearString(fullPath).split('/')

	def getIdAndEntityTypeFromPath(self, entityPathList, dbConn):		

		if len(entityPathList) == 1 and entityPathList[0].upper() == "ROOT":
			raise Exception("You cannot delete Root folder.")

		parentFolderName = entityPathList[-2]

		pathLen = len(entityPathList) - 2

		parentFolderRow = self.findParentFolderByNameAndPathLen(parentFolderName, pathLen, dbConn)

		if parentFolderRow is not None:
			
			folderToRemoveName = entityPathList[-1]

			folderToRemoveRow = dbConn.execute("""
				SELECT id, foldername FROM Folders as fold 
				JOIN FoldersTree as tree
				ON (fold.id = tree.child_id)
				WHERE tree.parent_id = %d
				AND fold.foldername = '%s'""" % (parentFolderRow[0], folderToRemoveName)).fetchone()

			print(folderToRemoveRow)

			return (folderToRemoveRow[0], EntityType.Folder)
		else:
			#todo
			pass


class AddFolderCommand(CommonDataQueriesMixin, object):
	"""Incapsulates add folder command logic"""

	def __init__(self, args):
		self.path = ''.join(args.path)
		self.foldername = ''.join(args.foldername)

	def execute(self):
		
		pathList = self.getPathList(self.path)

		pathLen = len(pathList) - 1

		parentFolder = pathList[-1]

		newFolder = self.clearString(self.foldername)

		with DatabaseProvider() as conn:

			parentFolderRow = self.findParentFolderByNameAndPathLen(parentFolder, pathLen, conn)
		
			if parentFolderRow is not None:

				with OpenDbTransaction(conn) as cursor:
					cursor.execute("INSERT INTO Folders (foldername) VALUES ('%s')" % newFolder)
					newId = cursor.lastrowid
					cursor.execute("INSERT INTO FoldersTree (parent_id, child_id, path_len) VALUES (%d,%d,%d)" % (parentFolderRow[0], newId, pathLen + 1))

#todo Rename and refacroting
class AddFileCommnad(CommonDataQueriesMixin, object):
	"""Incapsulated AddFileCommnad logic"""

	def __init__(self, args):
		self.path = ''.join(args.path)
		self.filename = ''.join(args.filename)
		self.content = ''.join(args.content)

	def execute(self):
		
		pathList = self.getPathList(self.path)

		parentFolderName = pathList[-1]

		pathLen = len(pathList) - 1

		newFilename = self.clearString(self.filename)

		fileContent = self.clearString(self.content)

		with DatabaseProvider() as conn:

			parentFolderRow = self.findParentFolderByNameAndPathLen(parentFolderName, pathLen, conn)

			if parentFolderRow is not None:

				with OpenDbTransaction(conn) as cursor:
					cursor.execute("""
						INSERT INTO 
						Files(filename, content, folder_id, size) 
						VALUES ('%s', '%s', %d, %d)""" % (newFilename, fileContent, parentFolderRow[0], len(fileContent)))


class RemoveAnyCommand(CommonDataQueriesMixin, object):
	"""Incapsulates RemoveAnyCommand logic"""

	def __init__(self, args):
		self.path = ''.join(args.path)

	def execute(self):
		print("remove_any command")

		fullPathList = self.getPathList(self.path)

		with DatabaseProvider() as conn:

			entityId, entityType = self.getIdAndEntityTypeFromPath(fullPathList, conn)
			#todo for file and folder

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

def checkDb():
	if not os.path.exists(DatabaseProvider.DatabaseFile):
		with DatabaseProvider() as conn:
			with OpenDbTransaction(conn) as cursor:
				cursor.execute(CREATE_TABLE_FOLDERS)
				cursor.execute(CREATE_TABLE_FILES)
				cursor.execute(CREATE_TABLE_FOLDERS_HIERACHY)
				cursor.execute(CREATE_ROOT_FOLDER)

def main():
	checkDb()
	parseArgs()

if __name__ == '__main__':
	main()