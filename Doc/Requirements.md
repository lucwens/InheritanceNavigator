## Summary
The Inheritance Navigator allows to quickly navigate between the overridden and base functions of a class. It uses the existing tools of visual studio but puts an extra layer of filtering on top of that:
- Only classes of certain source folders will be shown, effectively filtering out any other folders with source code coming from external libraries
- Classes can be found back quickly by typing name fragments in the UI of the tool
- The same goes for the virtual functions of the selected class
- Once a function is selected, the UI give an overview of the inheritance in 2 directions
	- A linear list of the class from which the function was overridden
	- A tree list of classes that override that function

As such this tools allows to get an good overview of which functions are overridden where and quickly navigate through them in order to make changes.

## Requirements

### Visual studio compatibility
It must work with Visual studio 2026 (must) and 2022 (nice to have)

### User interface
The user interface will be a dockable floating window that can be attached to the main Visual Studio user interface in a similar way as the Solution Explorer does.

It will contain different levels of filtering/search operation:
- Source folders selection item: via a setting (cog button) a list of source folders can be maintained. At the top level of the UI we can select which source folders are allowed as source by the means of check-boxes. Two extra buttons complement the cog settings button: enable all / disable all 
- Below the source folder selection item there is a class selection item. Here we can select 1 class from which we want to continue exploring the overridable functions. There will be an edit field where can type text fragments. These text fragments show a filtered list of class names below where we can select a class.
- When the class is select, in a similar way we have a virtual function list for that class, here we can also type text fragments to find back the function.
- Once we have the function selected as well, there are two windows below that that get updated
- The first window is the inherited from window that show a list of classes from which this function was inherited from. Double-clicking on an item will open the source file and go do the implementation (not the declaration) of that function.
- The second window is a hierarchical list of all functions that were derived from the selection virtual function. It can be a tree view, or it can also be a list view using indentation to show the depth of inheritance. Double-clicking on an item will open the source file and go do the implementation (not the declaration) of that function.
