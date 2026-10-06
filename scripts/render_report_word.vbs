Option Explicit
Dim wordApp, reportDoc, fileSystem, projectRoot, sourcePath, targetPath
Set fileSystem = CreateObject("Scripting.FileSystemObject")
projectRoot = fileSystem.GetParentFolderName(fileSystem.GetParentFolderName(WScript.ScriptFullName))
sourcePath = fileSystem.BuildPath(projectRoot, "docs\SmartSauda_Final_Report.docx")
targetPath = fileSystem.BuildPath(projectRoot, "docs\report-assets\word-render.pdf")
Set wordApp = CreateObject("Word.Application")
wordApp.Visible = False
wordApp.DisplayAlerts = 0
Set reportDoc = wordApp.Documents.Open(sourcePath, False, True)
reportDoc.Repaginate
WScript.Echo "Word rendered pages: " & reportDoc.ComputeStatistics(2)
reportDoc.ExportAsFixedFormat targetPath, 17
reportDoc.Close 0
wordApp.Quit
