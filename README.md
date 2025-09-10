# aplay
An ASCII player, mvp support for invoking VLC as a hidden audio subprocess
## Howto run aplay.py
1. Install the deps:
```pip3 install python-opencv pillow```
1. Invoke the shell:
Play in color with audio (from VLC)
```python aplay.py video.mp4 --color --audio```
Play in B/W with subtitles
```python aplay video.mp4 --srt```