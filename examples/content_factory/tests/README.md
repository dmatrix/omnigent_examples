# Tests

An executable spec for the two pieces of this example with behaviour too subtle
to verify by reading: the `publish_gate` policy (four interacting rules over two
differently-scoped pieces of session state) and `save_artifact` (one kind
appends, four truncate).

```bash
# plain python, no dependencies, from the repo root
python examples/content_factory/tests/test_publish_gate.py
python examples/content_factory/tests/test_save_artifact.py

# or under pytest
pytest examples/content_factory/tests/
```

Stdlib only. Both modules load their subject by file path and stub the
Omnigent import it uses for type aliases, so they run on a bare checkout with
no Omnigent installed.

`tests/` is a sibling of `tools/`, not a child of `tools/python/`, so nothing
here is auto-discovered as an agent tool. Keep it that way — a module placed
under `tools/python/` is imported at agent load time.
