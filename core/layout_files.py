"""Portable Crossing pictures; never export pairing or connection secrets."""
import copy
import json
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


def write(path, settings):
    document = {'format': 'beamer-crossing-layout', 'version': 1,
                'machine_id': settings['machine_id'], 'tiles': ways.derive_layout(settings, gap=0)}
    document['tiles'] = validate(document)
    Path(path).write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
