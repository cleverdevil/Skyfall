Skyfall
=======
Skyfall is a simple game written in [Python](https://python.org) using the
excellent [Pygame](https://pygame.org) project. The game allows the player to
control a falling skydiver, dodging helicopters, and collecting points for
flying through the clouds. The game is designed to be run on a macOS computer or
on the web, and was built for [Mission](https://missioncloud.com)'s 2024 AWS
re:Invent contest on the show floor.

Installation
------------
First, I recommend creating and activating a Python `virtualenv`, using Python
3.10 or higher. Then, you can simply run:

`pip install .`

This will download all of the dependencies and install them into your virtual
environment, enbabling you to run the game or build a distributable version as a
binary or on the web.

Running Locally
---------------
If you want to run the game from the CLI, after installation you can simply run:

`python main.py`

You control the Skydiver using the arrow keys on your keyboard. By default, when
running locally, the game maintains a leaderboard inside an
[SQLite](https://sqlite.org) database. The leaderboard will be displayed
in-game, and you can also print it out locally by running:

`sqlite3 leaderboard.db < results.sql`

The output is in an ASCII tabular format.

Building
--------

### Distributable Binary
Skyfall's included `Makefile` has a target named `app` that uses
[PyInstaller](https://pyinstaller.org) to create a distributable binary for
macOS. In their infinite wisdom, Apple has locked down the ability to run
self-built apps without going through a massive number of hoops, which I have
decided to skip, which makes things a bit less user-friendly, but is good
enough.

To build, run: `make app`. Inside the `application` folder will be a few shell
scripts and a hidden `.Skyfall.app` bundle. You can run the game by either
double clicking on `Skyfall`, or by executing it from the CLI. You can view the
latest leaderboard by double-clicking on `Leaderboard` or running it from the
CLI. It drops a text file onto your desktop.

### For the Web
Skyfall's included `Makefile` has a target named `web` that uses
[Pygbag](https://github.com/pygame-web/pygbag) to compile the game to
WebAssembly to play on the web. Simply run `make web`, and it will build the
`wasm` and serve it on `localhost`. The files can be copied to a web server to
make publicly available.

The web version works great both with keyboard and touch interfaces on phones
and tablets. When using touch, simply touch the left or right side of the screen
to move the skydiver.

NOTE: the web build does not feature a leaderboard.
