"""Explicit user operations for a private Ollama runtime and model downloads."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request

VERSION='0.35.1'
ASSETS={'x86_64':('amd64',1439658961,'9fcd79ac4575b2bd31b992eee18b1000c8ad126b451627c8f8cd091714cfbb10')}

def root():
    path=Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')/'angelos-open-llm'
    if path.is_symlink():raise ValueError('Каталог runtime не должен быть симлинком.')
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    return path

def binary():
    local=root()/'runtime/bin/ollama'
    return str(local) if local.is_file() else shutil.which('ollama')

def install(emit):
    if binary():
        emit('runtime',message='Ollama уже установлен. Нажми «Запустить сервер».')
        return
    if platform.machine() not in ASSETS:raise ValueError('Автоустановка поддерживает x86_64. Для этой архитектуры установи Ollama вручную.')
    if not shutil.which('zstd'):raise ValueError('Для распаковки нужен zstd.')
    arch,size,digest=ASSETS[platform.machine()]
    base=root()
    if shutil.disk_usage(base).free<6*1024**3:raise ValueError('Для установки нужно не менее 6 ГБ свободного места.')
    url=f'https://github.com/ollama/ollama/releases/download/v{VERSION}/ollama-linux-{arch}.tar.zst'
    with tempfile.TemporaryDirectory(prefix='.install-',dir=base) as tmp:
        archive=Path(tmp)/'runtime.tar.zst'; checksum=hashlib.sha256(); count=0
        with urllib.request.urlopen(url,timeout=60) as response,archive.open('wb') as out:
            while chunk:=response.read(1024*1024):
                count+=len(chunk)
                if count>size:raise ValueError('Архив больше заявленного размера.')
                checksum.update(chunk);out.write(chunk)
                emit('progress',message='Скачиваю Ollama…',completed=count,total=size)
        if count!=size or checksum.hexdigest()!=digest:raise ValueError('Контрольная сумма Ollama не совпала.')
        dest=Path(tmp)/'unpacked';dest.mkdir()
        proc=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        try:
            with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
                for member in tar:
                    target=(dest/member.name).resolve()
                    if not target.is_relative_to(dest):raise ValueError('Небезопасный путь в архиве.')
                    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):raise ValueError('Неподдерживаемый тип файла в архиве.')
                    if member.issym() or member.islnk():
                        link=(target.parent/member.linkname if member.issym() else dest/member.linkname).resolve()
                        if not link.is_relative_to(dest):raise ValueError('Ссылка выходит за пределы архива.')
                    # Archive is pinned and verified; reject unsafe paths, special files and privilege bits.
                    member.mode &= 0o755
                    tar.extract(member,dest,filter='fully_trusted') if hasattr(tarfile,'data_filter') else tar.extract(member,dest)
            if proc.wait()!=0:raise ValueError('Не удалось распаковать Ollama.')
        finally:
            if proc.poll() is None:proc.kill();proc.wait()
            proc.stdout.close()
        if not (dest/'bin/ollama').is_file():raise ValueError('В архиве нет Ollama.')
        target=base/'runtime'
        if target.exists():raise ValueError('Локальный runtime уже установлен.')
        dest.rename(target)
    emit('runtime',message='Ollama установлен. Теперь нажми «Запустить сервер».')

def local_config(config):
    parts=urllib.parse.urlsplit(config['url'])
    if config.get('protocol')!='ollama' or parts.scheme!='http' or parts.hostname not in ('127.0.0.1','localhost','::1') or parts.path.strip('/'):
        raise ValueError('Запуск и скачивание моделей доступны для локального Ollama URL.')
    port=parts.port or 11434
    return f'127.0.0.1:{port}'

def start(config,emit):
    host=local_config(config);exe=binary()
    if not exe:raise ValueError('Сначала установи Ollama.')
    env=dict(os.environ,OLLAMA_HOST=host)
    state=root();log=state/'server.log'
    if log.is_symlink():raise ValueError('Log must not be a symlink')
    with log.open('ab') as file:
        os.chmod(log,0o600)
        process=subprocess.Popen([exe,'serve'],env=env,stdout=file,stderr=file,stdin=subprocess.DEVNULL,start_new_session=True)
        try:
            code=process.wait(timeout=1)
            raise ValueError('Сервер завершился (код '+str(code)+'). Проверь журнал '+str(log))
        except subprocess.TimeoutExpired:pass
    emit('runtime',message='Сервер запущен. Нажми «Обновить список моделей» через несколько секунд. Журнал: '+str(log))

def pull(config,model,emit,opener,key):
    local_config(config)
    if not isinstance(model,str) or not model.strip() or len(model)>256 or any(c.isspace() for c in model):raise ValueError('Укажи ID модели, например qwen3:4b.')
    headers={'Content-Type':'application/json'}
    if key:headers['Authorization']='Bearer '+key
    req=urllib.request.Request(config['url'].rstrip('/')+'/api/pull',data=json.dumps({'model':model,'stream':True}).encode(),headers=headers)
    complete=False
    with opener.open(req,timeout=300) as response:
        while True:
            line=response.readline(65537)
            if not line:break
            if len(line)>65536:raise ValueError('Слишком большой ответ загрузчика.')
            event=json.loads(line)
            if event.get('error'):raise ValueError(str(event['error']))
            emit('progress',message=event.get('status','Загрузка модели…'),completed=event.get('completed',0),total=event.get('total',0))
            if event.get('status')=='success':complete=True
    if not complete:raise ValueError('Скачивание прервалось. Повторная загрузка продолжит его.')
    emit('runtime',message='Модель скачана: '+model)
