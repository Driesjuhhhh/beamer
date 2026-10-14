"""Portable Crossing pictures; never export pairing or connection secrets."""
import copy
import json
import os
import tempfile
from pathlib import Path

from core import settings_sync, ways


def read(path):
    if Path(path).stat().st_size > 1024 * 1024:
        raise ValueError('The layout file is too large.')
    return validate(json.loads(Path(path).read_text(encoding='utf-8')))


def validate(document):
    if not isinstance(document, dict) or document.get('format') != 'beamer-crossing-layout' or document.get('version') != 1:
        raise ValueError('This is not a Beamer Crossing layout.')
    envelope = settings_sync.message_data(False, 0, layout_state={
        'set_at': 0, 'by': document.get('machine_id'), 'tiles': document.get('tiles')})
    state = settings_sync.read_layout_state(envelope)
    if state is None:
        raise ValueError('The layout contains invalid screen positions or sizes.')
    return copy.deepcopy(state['tiles'])


def snapshot(settings):
    document = {'format': 'beamer-crossing-layout', 'version': 1,
                'machine_id': settings['machine_id'], 'tiles': ways.derive_layout(settings, gap=0)}
    document['tiles'] = validate(document)
    return document


def write(path, settings):
    document = snapshot(settings)
    Path(path).write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')


def saved_layouts(settings_path):
    path = Path(settings_path).with_name('saved-layouts.json')
    if not path.exists():
        return {}
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('The saved layouts file is too large.')
    library = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(library, dict) or len(library) > 100:
        raise ValueError('The saved layouts file is invalid.')
    for name, document in library.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError('A saved layout name is invalid.')
        validate(document)
    return library


def save_named(settings_path, name, settings):
    name = name.strip()
    if not name or len(name) > 80:
        raise ValueError('Choose a layout name between 1 and 80 characters.')
    library = saved_layouts(settings_path)
    matching = next((key for key in library if key.casefold() == name.casefold()), name)
    if matching not in library and len(library) >= 100:
        raise ValueError('You can save up to 100 layouts.')
    library[matching] = snapshot(settings)
    path = Path(settings_path).with_name('saved-layouts.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(library, handle, indent=2)
            handle.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return matching
