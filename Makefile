app:
	pyinstaller --noconfirm main.spec
	rm -rf application
	mkdir -p application
	cp -r dist/main.app application/.Skyfall.app
	cp run.sh application/Skyfall
	cp results.sh application/Leaderboard

web:
	pygbag --ume_block 0  --git .
