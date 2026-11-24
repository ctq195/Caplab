"""Validate and transactionally install prebuilt indices, using only stdlib."""
from __future__ import annotations
import argparse, ast, hashlib, json, os, shutil, struct, tempfile, uuid
from pathlib import Path
from contextlib import contextmanager

JSON_FILES = {'index_meta.json', 'documents.json', 'sources.json', 'claims.json', 'tags.json', 'sparse_index.json'}
MANIFEST = 'index_manifest.json'
class IndexError(ValueError): pass

def read(path):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e: raise IndexError(f'Cannot read {path.name}: {e}') from e

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''): h.update(part)
    return h.hexdigest()

def vector_shape(path):
    try:
        with path.open('rb') as f:
            if f.read(6)!=b'\x93NUMPY': raise IndexError('invalid NPY magic')
            version=f.read(2)
            if version==b'\x01\x00': size=struct.unpack('<H',f.read(2))[0]
            elif version in (b'\x02\x00',b'\x03\x00'): size=struct.unpack('<I',f.read(4))[0]
            else: raise IndexError('unsupported NPY version')
            if size>65536: raise IndexError('NPY header too large')
            header=ast.literal_eval(f.read(size).decode('latin1'))
            shape=header['shape'];dtype=header['descr']
            if dtype not in ('<f4','<f8','>f4','>f8','|f4','|f8') or len(shape)!=2: raise IndexError('expected numeric matrix')
            if any(type(x)!=int or x<=0 for x in shape): raise IndexError('invalid vector shape')
            if path.stat().st_size-f.tell()!=shape[0]*shape[1]*int(dtype[-1]): raise IndexError('truncated vector data')
            return tuple(shape)
    except (OSError,ValueError,KeyError,TypeError,struct.error) as e: raise IndexError(f'invalid vectors: {e}') from e

def validate_index(root, require_manifest=True):
    root=Path(root)
    if root.is_symlink() or not root.is_dir(): raise IndexError('index must be a real directory')
    entries=list(root.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries): raise IndexError('unknown directory or symlink in index')
    actual={p.name for p in entries}
    if actual-JSON_FILES-{'embeddings.npy',MANIFEST}: raise IndexError('unknown index files; refusing overwrite')
    if not JSON_FILES<=actual: raise IndexError('missing required index files')
    meta=read(root/'index_meta.json')
    if not isinstance(meta,dict) or meta.get('tier') not in ('free','paid') or not meta.get('kb_version'): raise IndexError('invalid tier/kb_version')
    for key in ('document_count','source_count','claim_count'):
        if type(meta.get(key))!=int or meta[key]<0: raise IndexError(f'invalid {key}')
    if meta['document_count']==0 or type(meta.get('dense_enabled'))!=bool: raise IndexError('empty index or invalid dense_enabled')
    if require_manifest:
        m=read(root/MANIFEST)
        if not isinstance(m,dict) or m.get('schema_version')!=1 or not isinstance(m.get('files'),dict): raise IndexError('invalid index manifest')
        if set(m['files'])!=actual-{MANIFEST}: raise IndexError('manifest coverage mismatch')
        for name,h in m['files'].items():
            if digest(root/name)!=h: raise IndexError(f'hash mismatch: {name}')
    docs=read(root/'documents.json'); sources=read(root/'sources.json'); claims=read(root/'claims.json'); tags=read(root/'tags.json'); sparse=read(root/'sparse_index.json')
    if not isinstance(docs,list) or len(docs)!=meta['document_count']: raise IndexError('document count mismatch')
    if not isinstance(sources,dict) or len(sources)!=meta['source_count']: raise IndexError('source count mismatch')
    if not isinstance(claims,dict) or not isinstance(tags,dict): raise IndexError('invalid claims/tags')
    claim_count=sum(len(v) if isinstance(v,list) else 1 for v in claims.values())
    if claim_count!=meta['claim_count']: raise IndexError('claim count mismatch')
    ids=set()
    for d in docs:
        if not isinstance(d,dict) or not isinstance(d.get('doc_id'),str) or d['doc_id'] in ids or not isinstance(d.get('fields'),dict) or not isinstance(d.get('sheet'),str): raise IndexError('invalid or duplicate document')
        ids.add(d['doc_id'])
    if not isinstance(sparse,dict) or not isinstance(sparse.get('inverted_index'),dict) or not isinstance(sparse.get('idf'),dict): raise IndexError('invalid sparse index')
    for token,postings in sparse['inverted_index'].items():
        if not isinstance(postings,list) or not isinstance(sparse['idf'].get(token),(float,int)): raise IndexError('invalid sparse term')
        for pair in postings:
            if not isinstance(pair,list) or len(pair)!=2 or type(pair[0])!=int or not 0<=pair[0]<len(docs) or not isinstance(pair[1],(int,float)) or pair[1]<=0: raise IndexError('invalid sparse posting')
    if meta['dense_enabled']:
        if vector_shape(root/'embeddings.npy')!=(len(docs),meta.get('embedding_dimension')): raise IndexError('embedding shape mismatch')
    elif 'embeddings.npy' in actual: raise IndexError('unexpected embeddings for sparse index')
    return meta

def seal_index(root):
    root=Path(root);validate_index(root,require_manifest=False)
    files={p.name:digest(p) for p in sorted(root.iterdir()) if p.name!=MANIFEST}
    fd,tmp=tempfile.mkstemp(dir=root.parent,prefix='.manifest-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump({'schema_version':1,'files':files},f,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,root/MANIFEST)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return validate_index(root)

@contextmanager
def install_lock(target):
    target.parent.mkdir(parents=True,exist_ok=True)
    lock=target.parent/('.'+target.name+'.install.lock')
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as e: raise IndexError('installation locked; inspect interrupted install before removing lock') from e
    os.close(fd)
    try: yield
    finally: lock.unlink(missing_ok=True)

def install_index(source,target):
    source=Path(source).absolute();target=Path(target).absolute()
    meta=validate_index(source)
    if target.is_symlink(): raise IndexError("target symlink refused")
    if source.resolve()==target.resolve(): return {'status':'reused','tier':meta['tier'],'backup':None}
    with install_lock(target):
        existing=False
        if target.is_symlink(): raise IndexError('target symlink refused')
        if target.exists():
            if not target.is_dir(): raise IndexError('target is not directory')
            existing=bool(list(target.iterdir()))
            if existing:
                validate_index(target,require_manifest=(target/MANIFEST).exists())
                if (target/MANIFEST).exists() and read(target/MANIFEST)==read(source/MANIFEST):
                    return {'status':'reused','tier':meta['tier'],'backup':None}
        stage=Path(tempfile.mkdtemp(dir=target.parent,prefix='.'+target.name+'.stage-'))
        backup=None
        try:
            for p in source.iterdir():shutil.copy2(p,stage/p.name)
            validate_index(stage)
            if target.exists():
                backup=target.parent/('.'+target.name+'.backups')/uuid.uuid4().hex
                backup.parent.mkdir(exist_ok=True);os.replace(target,backup)
            try: os.replace(stage,target)
            except BaseException:
                if backup is not None and not target.exists(): os.replace(backup,target)
                raise
            return {'status':'installed','tier':meta['tier'],'backup':str(backup) if backup else None}
        finally:
            if stage.exists():shutil.rmtree(stage)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['verify','seal','install']);p.add_argument('--index',type=Path,required=True);p.add_argument('--target',type=Path);a=p.parse_args()
    if a.command=='install' and a.target is None:p.error('install requires --target')
    try:r=seal_index(a.index) if a.command=='seal' else install_index(a.index,a.target) if a.command=='install' else validate_index(a.index)
    except (IndexError,OSError) as e:p.exit(1,str(e)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
