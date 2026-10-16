"""Explicit reuse of completed calls; preserve their original requests and provenance."""
import base64
import copy
import hashlib
import shutil
from pathlib import Path
import jsonschema
from .common import PACKAGE,read,write,digest,fingerprint,now


def import_page_job(source, target, origin_run):
    source,target=Path(source),Path(target)
    if target.exists() or not source.exists():
        return
    attempts=sorted(source.glob('attempt_*'))
    if not attempts or not (attempts[-1]/'state.json').exists() or read(attempts[-1]/'state.json')['status']!='complete':
        return
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,target)
    write(target/'reuse.json',{'origin_run':str(Path(origin_run).resolve()),'origin_stage':str(source.resolve()),
        'imported':now(),'original_request_sha256':digest(attempts[-1]/'request.json'),
        'policy':'Reuse only normally completed responses with identical scientific inputs; original output ceiling and citation-list ceiling may differ. Original requests, responses and metrics are retained.'})


def normalized(payload):
    payload=copy.deepcopy(payload)
    payload['options']['num_predict']=0
    def visit(node):
        if isinstance(node,dict):
            for key,value in node.items():
                if key=='sources' and isinstance(value,dict) and value.get('type')=='array':
                    value.pop('maxItems',None)
                visit(value)
        elif isinstance(node,list):
            for value in node:visit(value)
    visit(payload.get('format',{}))
    return payload


def verify_reuse(folder, previous, payload, image_hashes, source_ids):
    provenance=read(folder/'reuse.json')
    request_path=previous/'request.json'
    if digest(request_path)!=provenance['original_request_sha256']:
        raise ValueError('Imported request changed')
    original=read(request_path)
    images=original['messages'][1].pop('images',[])
    original_images=[hashlib.sha256(base64.b64decode(im,validate=True)).hexdigest() for im in images]
    prior=read(previous/'input.json')
    if original_images!=image_hashes or prior['source_ids']!=sorted(source_ids):
        raise ValueError('Imported source content differs')
    if prior['fingerprint']!=fingerprint({'payload':original,'images':original_images}):
        raise ValueError('Imported request does not match its original input fingerprint')
    if normalized(original)!=normalized(payload) or payload['options']['num_predict']<original['options']['num_predict']:
        raise ValueError('Imported scientific context, model, options or schema differ beyond allowed output ceilings')
    response=read(previous/'response.json')
    value=read(previous/'result.json')
    if not response.get('done') or response.get('done_reason')!='stop':
        raise ValueError('Only normally completed responses can be reused')
    import json
    if json.loads(response['message']['content'])!=value:
        raise ValueError('Imported parsed result differs from retained raw response')
    jsonschema.validate(value,read(PACKAGE/'schemas/page.json'))
    write(folder/'reuse_verified.json',{'verified':now(),'origin_run':provenance['origin_run'],
        'original_fingerprint':prior['fingerprint'],'current_request_fingerprint':fingerprint({'payload':payload,'images':image_hashes}),
        'original_num_predict':original['options']['num_predict'],'current_num_predict':payload['options']['num_predict'],
        'note':'This is an imported earlier response, not a fresh call under the new output ceilings. Scientific inputs match; original generation settings remain in request.json.'})
    return value
