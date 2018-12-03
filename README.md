# Python-Eye

A HTML window to explorative python. Triggered from your favorite editor.

Disclaimer: Well, just look at it.


## Super simple test setup.

Python Dependencies:

* `aiohttp` (and `py>=3.5`)
* `numpy`
* `pandas`
* `matplotlib`

Vim Dependencies:

* `mattn/webapi-vim`

All are hard for now. Don't ask.

* Run `kernel.py` in a python env with the modules you like.
* In vim `:source pyeye` and then:
  * in `NORMAL` mode, hit `<F5>` to send the current line.
  * in `VISUAL` mode, hit `<F5>` to send the current selection.

Also, if no like vim but want to try anyway, the plugin it basically sends this to `http://localhost:8080/`:

```json
{
  "code": "python code goes here"
}
```

GLHF!
