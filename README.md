Platonica - A Puzzle Game with Platonic Solids
Platonica is an engaging puzzle game featuring Platonic solids. Clone and solve the puzzles in your terminal while enjoying the challenge of geometric shapes.

Created By: Adeshina Adesola
GitHub Profile: Adeshinadesola

Running the Game
To run the game successfully, follow these steps:
* Ensure you have Python 3 installed. This game was developed with Python 3.10.7.
* Navigate to the game directory in your terminal: bash
* Install all the required dependencies using pip: bash
* Start the game by running the following command: bash  
Modifying the Game with Environment Variables
You can "hack" the game by using environment variables to apply special modifiers. Here are the available modifiers:

* SKIP_TUTORIAL=1: Launch the game with this variable to skip the tutorial when starting.
* START_LEVEL=<number>: Begin the game at a specific level, bypassing all previous levels. Use a number to select the starting level:
    * 0: Tetrahedron
    * 1: Cube
    * 2: Octahedron
    * 3: Icosahedron
    * 4: Dodecahedron
* OVER_EASY=1: Activate this variable to start every puzzle in the solved state. To register a move, you'll need to rotate a face three times.
* 
Known Bugs
While we've done our best to create a seamless gaming experience, there are a couple of known issues:
* Clicking Bug: Occasionally, clicking on the screen may stop working. If this happens, try clicking out of the game window and then back into it. We've attempted to fix this issue without success, and it may be related to pygame on Mac.
* Rotation Bug: Sometimes, the rotation feature may stop working. Although we suspect it's our bug, we couldn't reproduce it consistently to identify a solution. If this occurs, you'll need to exit the game and restart it to resolve the problem.
* 
Special Thanks
We extend our gratitude to our dedicated playtesters who helped improve the game and make it more enjoyable for all players. Your feedback and support are greatly appreciated.

