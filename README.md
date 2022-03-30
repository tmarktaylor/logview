# logview

GitHub action log archive viewer

Command line tool processes GitHub actions log archive .zip file.

- Consumes previously downloaded Log archives.
- Scans for specific strings like "warning" or "error" and
  summarizes findings at the end.
- Intended for use in a terminal either stand alone or one
  lauched by an IDE.
- Colorizes phrases.
- Override default configuration by providing a .toml file. 

Requires Python Package Index packages colorama and tomli.
