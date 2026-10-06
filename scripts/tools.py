"""Typed desktop tools shared by the chat agent and stdio MCP adapter."""
import json
from pathlib import Path
import subprocess


def command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Desktop command failed').strip()[:2000])
    return result.stdout.strip()[:24000]


def ipc(name, *args):
    return command(['qs', '-c', 'angelos', 'ipc', 'call', 'angelos', name, *map(str, args)])


def text(value, limit=256):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError('Invalid text argument')
    return value


def choice(value, values):
    if value not in values or not isinstance(value, str):
        raise ValueError('Unsupported argument: ' + str(value))
    return value


def number(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Invalid numeric argument')
    return value


def shell_state(args):
    state = json.loads(ipc('status'))
    return {key: state[key] for key in ('theme','flavor','bar','plugins','screens') if key in state}


def windows(args):
    data = json.loads(command(['niri','msg','-j','windows']))
    return [{key: row.get(key) for key in ('id','title','app_id','workspace_id','is_focused')} for row in data[:100]]


def workspaces(args):
    return json.loads(command(['niri','msg','-j','workspaces']))[:100]


def power(args):
    out=[]
    for folder in Path('/sys/class/power_supply').glob('*'):
        row={'name':folder.name}
        for key in ('type','status','capacity','online'):
            file=folder/key
            if file.is_file():row[key]=file.read_text().strip()
        out.append(row)
    return out


def wallpapers(args):
    root=Path.home()/'Pictures'
    found=[]
    for file in root.rglob('*'):
        if file.is_file() and file.suffix.lower() in ('.png','.jpg','.jpeg','.webp') and file.resolve().is_relative_to(root.resolve()):
            found.append(str(file.resolve()))
            if len(found)>=100:break
    return sorted(found)


def set_wallpaper(args):
    path=Path(text(args.get('path'),2048)).expanduser().resolve()
    if not path.is_relative_to((Path.home()/'Pictures').resolve()) or not path.is_file() or path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
        raise ValueError('Choose an existing image from get_wallpapers in ~/Pictures')
    return ipc('wallpaper',str(path))


def focus(args):
    window=number(args.get('id'),1,2**31-1)
    return command(['niri','msg','action','focus-window','--id',str(window)])


def schema(name, description, properties, handler, read_only=False):
    return {'name':name,'description':description,'parameters':{'type':'object','properties':properties,
            'required':list(properties),'additionalProperties':False},'handler':handler,'read_only':read_only}


def enum(values): return {'type':'string','enum':values}


TOOLS = [
    schema('get_shell_state','Read current theme, bar, enabled plugins and screens.',{},shell_state,True),
    schema('get_windows','Read the current niri window list.',{},windows,True),
    schema('get_workspaces','Read niri workspace information.',{},workspaces,True),
    schema('get_power','Read battery and power status.',{},power,True),
    schema('get_wallpapers','List up to 100 available wallpaper images in ~/Pictures.',{},wallpapers,True),
    schema('search_settings','Find native AngelOS settings by query.',{'query':{'type':'string','maxLength':256}},lambda a:ipc('searchSettings',text(a.get('query'))),True),
    schema('open_settings','Open the native setting matching the query.',{'query':{'type':'string','maxLength':256}},lambda a:ipc('openSetting',text(a.get('query')))),
    schema('set_theme','Change AngelOS light/dark/automatic theme.',{'mode':enum(['light','dark','auto','toggle'])},lambda a:ipc('theme',choice(a.get('mode'),['light','dark','auto','toggle']))),
    schema('set_motion','Change desktop animation level.',{'level':enum(['full','calm','off'])},lambda a:ipc('motion',choice(a.get('level'),['full','calm','off']))),
    schema('set_bar','Change native bar layout.',{'style':enum(['taskbar','top','island','dock','capsules','windose'])},lambda a:ipc('bar',choice(a.get('style'),['taskbar','top','island','dock','capsules','windose']))),
    schema('switch_workspace','Switch to a numbered workspace.',{'workspace':{'type':'integer','minimum':1,'maximum':50}},lambda a:ipc('ws',number(a.get('workspace'),1,50))),
    schema('focus_window','Focus a known window ID from get_windows.',{'id':{'type':'integer','minimum':1}},focus),
    schema('media_control','Control the active music/video player.',{'action':enum(['play','pause','toggle','next','previous'])},lambda a:ipc('media',choice(a.get('action'),['play','pause','toggle','next','previous']))),
    schema('volume_control','Increase/decrease audio volume or toggle mute.',{'action':enum(['up','down','mute'])},lambda a:ipc({'up':'volumeUp','down':'volumeDown','mute':'mute'}[choice(a.get('action'),['up','down','mute'])])),
    schema('set_wallpaper','Apply an existing image from get_wallpapers as wallpaper.',{'path':{'type':'string','maxLength':2048}},set_wallpaper),
    schema('open_launcher','Open the native launcher with a search query.',{'query':{'type':'string','maxLength':256}},lambda a:ipc('launcherWith',text(a.get('query'))))
]
BY_NAME={t['name']:t for t in TOOLS}


def definition(name, arguments):
    if name not in BY_NAME or not isinstance(arguments,dict):
        raise ValueError('Unknown tool or invalid arguments')
    tool=BY_NAME[name]
    props=tool['parameters']['properties']
    if set(arguments)!=set(props):raise ValueError('Missing or unknown tool arguments')
    for key, prop in props.items():
        value=arguments[key]
        if prop['type']=='string':text(value,prop.get('maxLength',256))
        elif prop['type']=='integer':number(value,prop.get('minimum',1),prop.get('maximum',2**31-1))
        if 'enum' in prop:choice(value,prop['enum'])
    return tool


def execute(name, arguments):
    tool=definition(name,arguments)
    return {'ok':True,'result':tool['handler'](arguments)}


def exported():
    return [{'type':'function','function':{k:t[k] for k in ('name','description','parameters')}} for t in TOOLS]
