# Parxy Terminal UI specification

The terminal UI serve as a quick entry-point for testing Parxy functionalities. From the terminal UI users can explore a folder with documents, process few or all of them and get the corresponding markdown. Users can then visualize the markdown obtained by using each supported parser and compare against each other in a two sided interface.

Three are the main screens envisioned

1. Folder selection, everything starts with a folder. User can pass as argument to the command line when triggering the tui or selecting from the tui itself
2. Browsing the folder for supported files. Here files are listed and user can navigate between folders. Files can be selected and parsing can be triggered. For each file is reported if parsing was done
3. Viewing file parsing information and see the corresponding markdown. In case a file was parsed by more than one parser 

In the following screens are represented with simplified ASCII diagrams.

This is the basic chrome of the interface.

|-------------------------------------------------------------------|
| ▣ parxy                                           ctrl+p commands |
|                                                                   |
|                                                                   |
|                                                                   |
|                                                                   |
|                                                                   |
| status                                                      hints |
|-------------------------------------------------------------------|


- "ctrl+p command" is also clicable and the command palette is shown when clicked
- clicking on the status will show a modal with the status of long running processes
- hints is a variable section that is populated in case of need
- the parxy logo is a clickable button that trigger a back navigation in the screens, for example when viewing a single file clicking it returns to the folder exploration, from the folder exploration clicking it return to the folder selection


## Folder selection

|-------------------------------------------------------------------|
| ▣ parxy                                           ctrl+p commands |
|                                                                   |
| Select a folder                                                   | 
|                                                                   |
|  Type here to search                                              | 
|                                                                   |
| ├── dist                                                          | 
| ├── docs                                                          | 
| ├── examples                                                      | 
| ├── imgs                                                          | 
| ├── notes                                                         | 
| ├── questions                                                     | 
| ├── reference                                                     | 
|                                                                   |
| status                                                      hints |
|-------------------------------------------------------------------|



## Browsing the folder


|-------------------------------------------------------------------|
| ▣ parxy / folder name                            ctrl+p commands |
|                                                                   |
| Select a folder           | File list                             | 
|                           |                                       |
|  Type here to search      | search files                          | 
|                           |                                       |
| ├── dist                  | First file.pdf   processed 14 pages   | 
| ├── docs                  | second file.pdf   processed 14 pages  | 
| ├── examples              |                                       |
| ├── imgs                  |                                       | 
| ├── notes                 |                                       | 
| ├── questions             |                                       | 
| ├── reference             |                                       | 
|                                                                   |
| status                                                      hints |
|-------------------------------------------------------------------|


## Viewing the file



|-------------------------------------------------------------------|
| ▣ Folder name / file name                        ctrl+p commands |
|                                                                   |
|                                                                   |
|                                                                   |
|                                                                   |
|                                                                   |
| status                                                      hints |
|-------------------------------------------------------------------|








## Navigation

Navigation between screens happen by clicking on buttons or by global shortcuts

- Ctrl+E, shows the folder browsing screen with the currently selected folder
- Ctrl+K, shows the viewer screen for the currently focused file. Works also when pressing spacebar when file list component is focused
- Ctrl+P, shows the command palette
- Ctrl+I, show/hide the sidebar with additional information in screens that supports it


## History

The TUI saves user preferences and information in the user folder under `.parxy`.

It saves the history of folders browsed every time a new folder is selected to browse at startup. The list of sessions can be retrieved via the command menu or the shortcut Ctrl+H that shows a modal with the most recent sessions that are searchable for a quick find. It is stored the date and the folder absolute path.

