# _future plugins

a parking lot for plugins that aren't built yet — ideas, specs, and stubs.

**the loader ignores anything in `plugins/` whose name starts with `_`**, so nothing in here loads or shows up in the ui. it sits right next to the real plugins on purpose: when a future plugin is ready, it just moves up one level —

```
plugins/_future/letta/   ->   plugins/letta/
```

— drops out of the parking lot, and goes live on the next restart. that's the whole lifecycle: park the idea here, graduate it when it works.

each future plugin gets its own folder with whatever exists so far — a notes file, a partial stub, a copied artifact.

## a note on what's parked here

the current residents (letta, burr's tunnel) aren't really *device* plugins — they're about letting a **remote or external mind reach habitat**, not adding a new piece of local hardware. that hints the plugin system may eventually want two shapes:

- **device** plugins — hardware habitat controls directly (colmi, lovense, polar).
- **transport / bridge** plugins — ways something *outside* reaches *in*.

not a decision, just the question these two raised. worth holding when we build them.
