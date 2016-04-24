Ensure the virtualenv installation works on several Linux distros:

1. `make check`
2. `make ve`
3. source ve/bin/activate
4. `make pip`
5. `make install`
6. `which fpos` points to `.../ve/bin/fpos`
7. `fpos init example /tmp/example.db
8. `./examples/update.exp example examples/transactions.csv`
9. `diff -u examples/example.db /tmp/example.db`
10. `fpos show example`
11. `fpos show --save 1000 example`

Ensure the install-user installation works on several Linux distros. Note this
may require installing various system-wide dependencies.

1. `make pip`
2. `make install-user`
3. `which fpos` points to `~/.local/bin/fpos`
4. `fpos init example /tmp/example.db
5. `./examples/update.exp example examples/transactions.csv`
6. `diff -u examples/example.db /tmp/example.db`
7. `fpos show example`
8. `fpos show --save 1000 example`

Test that the following succeed on OSX:

1. `curl -fsSL -o fposx https://raw.githubusercontent.com/amboar/fpos/master/bin/fposx && chmod +x fposx`
2. `./fposx install`
3. `./fposx run`
6. `fpos init example /tmp/example.db
7. `~/.local/usr/src/fpos/examples/update.exp example ~/.local/usr/src/fpos/examples/transactions.csv`
8. `diff -u ~/.local/usr/src/fpos/examples/example.db /tmp/example.db`
9. `fpos show example`
10. `fpos show --save 1000 example`
11. `logout`
12. `./fposx upgrade`
13. `./fposx uninstall`

To release:
1. Update `setup.py` to reflect the release version.
2. Create a signed tag
3. Push to github
