"""Maintainer check: pip install jsonschema, then run this script (no state writes)."""
import copy,json,re,sys
from pathlib import Path
import jsonschema
import caplab_state as state
ROOT=Path(__file__).resolve().parents[1]
def main():
 schema=json.loads((ROOT/'references/schemas/caplab-state.schema.json').read_text());patch_schema=json.loads((ROOT/'references/schemas/caplab-patch.schema.json').read_text())
 jsonschema.Draft202012Validator.check_schema(schema);jsonschema.Draft202012Validator.check_schema(patch_schema)
 validator=jsonschema.Draft202012Validator(schema);checks=[]
 def check(name,value):
  errors=list(validator.iter_errors(value))
  if errors:raise ValueError(name+': '+ '; '.join(str(list(x.path))+' '+x.message for x in errors))
  checks.append(name)
 check('empty runtime state',state.empty_state())
 for name,section in [('intake','intake'),('profile','profile'),('path','path_decision'),('cycle','cycle_plan'),('review','reviews')]:
  text=(ROOT/'references/contracts'/(name+'-contract.md')).read_text()
  blocks=[json.loads(x) for x in re.findall(r'```json\s*(.*?)```',text,re.S)]
  value=state.empty_state();value['sections'][section]=[blocks[0]] if section=='reviews' else blocks[0]
  check(name+' contract structure',value)
  if name=='intake':
   jsonschema.validate(blocks[1],patch_schema)
   if state.validate_patch(blocks[1],state.empty_state()):raise ValueError('contract patch rejected')
   checks.append('contract patch envelope accepted')
 # Fully confirmed fixture exercises date regex and strict personal fields.
 sys.path.insert(0,str(ROOT/'tests'));from fixtures import ready_intake
 ready=state.empty_state();ready['sections']['intake']=ready_intake();check('confirmed personal facts',ready)
 for label,mutation in [('missing source',lambda s:s['sections']['intake']['major'].pop('source_ids')),('wrong type',lambda s:s['sections']['intake'].update(personal_facts='invalid')),('bad age date',lambda s:s['sections']['intake']['personal_facts']['age'].update(as_of='not-date'))]:
  bad=copy.deepcopy(ready);mutation(bad)
  if not list(validator.iter_errors(bad)):raise ValueError('schema accepted '+label)
  checks.append('reject '+label)
 print(json.dumps({'status':'ok','checks':checks,'note':'JSON Schema and Python business checks are complementary'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
