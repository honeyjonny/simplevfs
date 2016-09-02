
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


class ListCommand(object):
	"""Incapsulates list command logic"""

	selectChildFoldersTemplate = """
			SELECT id, foldername 
			FROM Folders as fold 
			JOIN FoldersTree as tree 
			ON (fold.id = tree.child_id) 
			WHERE tree.parent_id = %d"""

	def __init__(self, args):
		pass

	def execute(self):
		with DatabaseProvider() as conn:
			folderDepth = 1
			rootFolder = conn.execute("""
				SELECT id, foldername 
				FROM Folders 
				WHERE foldername = 'Root'""").fetchone()
			self.printFolderStructure(folderDepth, rootFolder, conn)


	def printFolderStructure(self, folderDepth, folderRow, dbConn):

		childFoldersList = self.getChildsForFolderId(folderRow[0], dbConn)

		childFiles = self.getFilesByFolderId(folderRow[0], dbConn)


		folderSize = self.getChildsFoldersSize(childFoldersList, dbConn)

		folderSize = folderSize + self.sumFilesSize(childFiles)


		childsFoldersLen = len(childFoldersList)

		filesNumber = len(childFiles) if len(childFiles) > 0 else None


		self.printFolder(folderDepth, folderRow[1], folderSize, childsFoldersLen, filesNumber)

		folderDepth += 1

		for childFile in childFiles:
			self.printFile(folderDepth, childFile[0], childFile[1])

		for childFolderRow in childFoldersList:
			self.printFolderStructure(folderDepth, childFolderRow, dbConn)

	def getChildsForFolderId(self, folderId, dbConn):
		return dbConn.execute(self.selectChildFoldersTemplate % folderId).fetchall()

	def getChildsFoldersSize(self, childFoldersList, dbConn):
		
		size = 0

		for folder in childFoldersList:

			filesInFolder = self.getFilesByFolderId(folder[0], dbConn)

			filesSize = self.sumFilesSize(filesInFolder)

			subFolders = self.getChildsForFolderId(folder[0], dbConn)

			subFoldersSize = self.getChildsFoldersSize(subFolders, dbConn)

			size = size + filesSize + subFoldersSize

		return size

	def getFilesByFolderId(self, folderId, dbConn):
		return dbConn.execute("""
			SELECT filename, size 
			FROM Files as files 
			WHERE files.folder_id = %d""" % folderId).fetchall()

	def sumFilesSize(self, filesInFolderList):
		return sum(map(lambda fileRow: fileRow[1], filesInFolderList))

	def printFile(self, depth, fileName, size):
		signs = '-' * depth
		print("%s %s (Type: file, Size: %d bytes)" % (signs, fileName, size))

	def printFolder(self, depth, folderName,  folderSize, childsFoldersNumber, filesNumber = None):
		signs = '-' * depth

		if filesNumber is not None:
			print("""%s %s (Size: %d, Folders: %d, Files: %d)""" % (signs, folderName, folderSize, childsFoldersNumber, filesNumber))
		else:
			print("""%s %s (Size: %d, Folders: %d)""" % (signs, folderName, folderSize, childsFoldersNumber))


class EntityType(Enum):
	"""Enumerate types of entities for commands actions"""	
	Folder = 1
	File = 2

		
class CommonDataQueriesMixin(object):
	"""Mix-ins into command class for reuse of db acces code"""

	def findParentFolderByNameAndPathLen(self, parentFolderName, pathLen, dbConn):

		parentFolderRow = None

		if pathLen == 0:

			parentFolderRow = dbConn.execute("""
				SELECT id, foldername 
				FROM Folders 
				WHERE foldername = 'Root'""").fetchone()

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

			entityToRemoveName = entityPathList[-1]

			folderToRemoveRow = dbConn.execute("""
				SELECT id, foldername FROM Folders as fold 
				JOIN FoldersTree as tree
				ON (fold.id = tree.child_id)
				WHERE tree.parent_id = %d
				AND fold.foldername = '%s'""" % (parentFolderRow[0], entityToRemoveName)).fetchone()

			fileToRemoveRow = dbConn.execute("""
				SELECT id, filename FROM Files
				WHERE folder_id = %d
				AND filename = '%s'""" % (parentFolderRow[0], entityToRemoveName)).fetchone()

			if folderToRemoveRow is not None and fileToRemoveRow is None:
				#print(folderToRemoveRow)
				return (folderToRemoveRow[0], EntityType.Folder)

			elif fileToRemoveRow is not None and folderToRemoveRow is None:
				#print(fileToRemoveRow)
				return (fileToRemoveRow[0], EntityType.File)
			else:
				raise Exception("Not found resource on path: %s" % '/'.join(entityPathList))

		else:
			raise Exception("Not found path: %s" % '/'.join(entityPathList[:-1]))



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
					cursor.execute("""
						INSERT INTO FoldersTree (parent_id, child_id, path_len) 
						VALUES (%d,%d,%d)""" % (parentFolderRow[0], newId, pathLen + 1))


class AddFileCommand(CommonDataQueriesMixin, object):
	"""Incapsulated AddFileCommand logic"""

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

		fullPathList = self.getPathList(self.path)

		with DatabaseProvider() as conn:

			entityId, entityType = self.getIdAndEntityTypeFromPath(fullPathList, conn)

			with OpenDbTransaction(conn) as cursor:
			
				if entityType == EntityType.File:

					cursor.execute("""DELETE FROM Files WHERE id = %d""" % entityId)

				elif entityType == EntityType.Folder:

					cursor.execute("""DELETE FROM Folders WHERE id = %d""" % entityId)

		
class ShowFileCommand(CommonDataQueriesMixin, object):
	"""Incapsulates ShowFileCommand logic"""

	def __init__(self, args):
		self.path = ''.join(args.path)

	def execute(self):

		fullPathList = self.getPathList(self.path)

		with DatabaseProvider() as conn:

			entityId, entityType = self.getIdAndEntityTypeFromPath(fullPathList, conn)

			if entityType == EntityType.File:

				fileRow = conn.execute("""
					SELECT id, filename, content 
					FROM Files 
					WHERE id = %d""" % entityId).fetchone()

				print("%s" % fileRow[2])

			elif entityType == EntityType.Folder:

				print("Show folder content not implemented yet, try `list` command.")

		
class EditCommand(CommonDataQueriesMixin, object):
	"""Incapsulates EditCommand logic"""

	def __init__(self, args):
		self.path = ''.join(args.path)
		self.newname = ''.join(args.name) if args.name is not None else None
		self.newcontent = ''.join(args.content) if args.content is not None else None

	def execute(self):

		fullPathList = self.getPathList(self.path)

		with DatabaseProvider() as conn:

			entityId, entityType = self.getIdAndEntityTypeFromPath(fullPathList, conn)

			with OpenDbTransaction(conn) as cursor:

				if entityType == EntityType.File:

					if self.newname is not None:

						newName = self.clearString(self.newname)

						self.setNewFilename(newName, entityId, cursor)

					if self.newcontent is not None:

						newContent = self.clearString(self.newcontent)

						self.setNewFileContent(newContent, entityId, cursor)

				elif entityType == EntityType.Folder:

					if self.newname is not None:

						newName = self.clearString(self.newname)					

						self.setNewFolderName(newName, entityId, cursor)


	def setNewFilename(self, newFilename, fileId, dbCursor):
		dbCursor.execute("""
			UPDATE Files
			SET filename = '%s'
			WHERE id = %d""" % (newFilename, fileId))

	def setNewFileContent(self, newFileContent, fileId, dbCursor):
		dbCursor.execute("""
			UPDATE Files 
			SET content = '%s', size = %d
			WHERE id = %d""" % (newFileContent, len(newFileContent), fileId))

	def setNewFolderName(self, newFolderName, folderId, dbCursor):
		dbCursor.execute("""
			UPDATE Folders
			SET foldername = '%s'
			WHERE id = %d""" % (newFolderName, folderId))
		

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
	add_file.set_defaults(func=AddFileCommand)

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