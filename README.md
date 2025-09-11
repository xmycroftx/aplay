# aplay
An ASCII player, mvp support for invoking VLC as a hidden audio subprocess
## Howto run aplay.py
Download the dependencies:
* Install with pip: ```pip3 install python-opencv pillow```

Invoke the shell:
* Play in color with audio (from VLC): ```python aplay.py video.mp4 --color --audio```
* Play in B/W with subtitles: ```python aplay video.mp4 --srt```

Example running in vscode terminal:
![image](https://github.com/xmycroftx/aplay/blob/main/screeny.png?raw=true)
