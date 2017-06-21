# dwm-pytus
## A status bar script for dwm written in python

This is a very basic python script that retrieves and formats information about the system and sets the resulting string as the `WM_NAME` of the root window of X. In dwm this has the effect to set the status bar text.

### Appearance
This is how the status bar looks. Bear in mind that font and colors are specified by dwm, not by this program.


![bar screenshot](https://raw.githubusercontent.com/chftyrol/dwm-pytus/master/screenshots/bar.png)


![clean screenshot](https://raw.githubusercontent.com/chftyrol/dwm-pytus/master/screenshots/clean.png)


The icons are Unicode symbols and to display them you will need a font that supports them, such as [this](https://aur.archlinux.org/packages/ttf-font-icons/).

### System Information
At the moment the script displays the current information:

* Volume: by polling ALSA.
* Uptime
* Location of the VPN Server currently in use.
* Used memory
* Battery status and charge
* Date
* Time

These are the ones I need and at the moment I don't think I'll add anything else. If you are interested in adding something feel free to do so and if you feel someone else could benefit from it you can make a pull request.

### Formatting
All the elements are formatted for my needs and tastes. The code contains a class called `Formatter` whose only purpose is to format the information it is provided.
If you'd like you can tweak that to your liking.

At the moment I use Unicode symbols as icons, so to display them correctly you will need a font supporting those symbols, like [this one](https://aur.archlinux.org/packages/ttf-font-icons/).

### Installation
Clone the repository recursively, like so:
```sh
$ git clone --recursive https://github.com/chftyrol/dwm-pytus.git
```

### Running
Simply run the script `dwm-pytus.py`. You will need Python 3 to do so.
A few command line options are available to change the behavior of the program. To check them out run `dwm-pytus.py -h`.

### License
dwm-pytus is Free Software, released under the GPL version 3 or later. When I say *Free* I mean free as in free speech not as in free beer. To learn more about this you can check out the [Free Software Foundation](https://fsf.org).
