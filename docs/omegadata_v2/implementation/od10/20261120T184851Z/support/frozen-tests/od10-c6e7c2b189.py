"""OD10 anonymous bookkeeping / literal scalar tests. No financial source observations."""
from dataclasses import replace
from datetime import UTC,date,datetime,timedelta,timezone
from decimal import Decimal,localcontext
from pathlib import Path
import hashlib
import json
import threading
import pytest

D=date(2020,1,2)
K=datetime(2020,1,3,tzinfo=UTC)

def record(**kw):
 from omegadata.canonical_storage.contracts import Observation
 return replace(Observation(observation_id='control-0001',observation_revision_id='revision-1',source_id='control-source',source_artifact_identity='control-artifact',source_record_identity='control-row',trade_date=D,session_date=D,known_from=K,field_semantics='CONTROL_SCALAR',value=Decimal('1.2500'),security_id='control-security',listing_id='00001',exchange='CANARY-X',symbol_as_reported='CONTROL',series_as_reported='CONTROL',publisher_identity='control-publisher',source_row_ordinal=1,parser_version='control-parser/v1',schema_version='control/v1',source_evidence_id='NON_MARKET_CONTROL',source_rights_state='NON_MARKET_CONTROL',source_authority_digest='a'*64,observation_classification='NON_MARKET_STRUCTURAL_CONTROL',quality_state='UNVERIFIED',price_basis='RAW_UNADJUSTED',volume_basis='RAW',currency='CONTROL',price_unit='CONTROL',volume_unit='CONTROL',consumer_profile='AUDIT',economic_valid_from=D),**kw)

def database(tmp_path):
 from omegadata.canonical_storage.store import CanonicalStore
 return CanonicalStore(tmp_path/'store',disposable_root=tmp_path)

def commit(db,rows=None,op='operation-1',parent=None,**kw):
 from omegadata.canonical_storage.contracts import DatasetDefinition
 definition=DatasetDefinition('control-dataset','source_observations','RAW','canonical/v1','RAW_UNADJUSTED','AUDIT',('control-source',),'COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE')
 definition=replace(definition,**kw.pop('definition',{}))
 return db.commit(definition,(record(),) if rows is None else rows,operation_id=op,parent_version=parent,expected_partitions=('CANARY-X/2020-01',),**kw)

def query(db,version,**kw):
 from omegadata.canonical_storage.contracts import Query
 return db.query(replace(Query(version,'control-dataset',D,D+timedelta(days=1),K,'RAW_UNADJUSTED','AUDIT'),**kw))

GROUPS=[f'{p}{i:02}' for p,n in [('S',6),('L',7),('V',5),('M',6),('T',6),('C',4),('E',4),('Q',7),('R',3),('G',4)] for i in range(1,n+1)]
@pytest.mark.parametrize('group',GROUPS)
def test_od10_acceptance(group,tmp_path):
 from omegadata.canonical_storage import schema
 from omegadata.canonical_storage.contracts import StorageError,Query
 if group.startswith('S'):
  row=record()
  if group=='S01':assert schema.from_table(schema.to_table((row,),'canonical/v1'))==(row,)
  elif group=='S02':
   value=Decimal('0.'+'1'*90)
   coded=schema.encode_decimal(value,'CALCULATION')
   assert schema.decode_decimal(coded).as_tuple()==value.as_tuple() and coded['fixed'] is None
  elif group=='S03':
   with pytest.raises(StorageError,match='PRECISION'):schema.encode_decimal(Decimal('1e-90'),'RAW')
  elif group=='S04':
   rows=(replace(row,value=None,value_state='MISSING'),replace(row,observation_revision_id='zero',value=Decimal(0)))
   assert [r.value for r in schema.from_table(schema.to_table(rows,'canonical/v1'))]==[None,Decimal(0)]
  elif group=='S05':
   r=replace(row,known_from=K.astimezone(timezone(timedelta(hours=5,minutes=30))))
   assert schema.from_table(schema.to_table((r,),'canonical/v1'))[0].known_from==K
   with pytest.raises(StorageError):replace(row,known_from=K.replace(tzinfo=None))
  elif group=='S06':assert schema.from_table(schema.to_table((row,),'canonical/v1'))[0].listing_id=='00001'
  return
 db=database(tmp_path)
 if group.startswith('L'):
  from omegadata.canonical_storage.admission import ProvenanceLedger,SourceBinding,admit_comparison
  from test_od09_reconciliation import controls
  from omegadata.reconciliation.engine import reconcile_context
  _,x,left,right=controls();ledger=ProvenanceLedger()
  if group=='L01':
   from omegadata.parsers.contracts import ParseResult
   v=ParseResult('PARSED_UNVERIFIED','a'*64)
   ref=ledger.pin('source_observations','parser-control',v,K)
   assert ledger.get(ref)==v and not ledger.financial_eligible(ref)
  elif group=='L02':
   a=ledger.pin('instrument_identity_revisions','identity',x.universe.identity,K)
   b=ledger.pin('session_calendar','calendar',x.universe.calendar,K)
   assert ledger.get(a)==x.universe.identity and ledger.get(b)==x.universe.calendar
  elif group=='L03':
   from omegadata.canonical_storage.admission import verify_proof
   from omegadata.reconciliation.dependencies import UpstreamProof
   with pytest.raises(StorageError):verify_proof(None,K)
   assert UpstreamProof is not None
  elif group=='L04':
   from omegadata.universe.snapshots import get_universe_as_of
   from omegadata.universe.contracts import EligibilityPolicy
   p=EligibilityPolicy('control-membership',view='MEMBERSHIP')
   s=get_universe_as_of(x.universe,D,K,p,x.universe.source_snapshot_id)
   ref=ledger.pin('universe_snapshots','snapshot',s,K,context=(x.universe,p))
   assert len(ledger.get(ref).decisions)==len(s.decisions)
  else:
   ledger.pin_observations((left,right))
   binding=SourceBinding.from_observation(left)
   if group=='L05':assert admit_comparison(x,reconcile_context(x),ledger,(left.observation_id,right.observation_id),False).financial_eligible is False
   elif group=='L06':
    with pytest.raises(StorageError,match='SCOPE'):admit_comparison(replace(x,right=()),reconcile_context(replace(x,right=())),ledger,(left.observation_id,right.observation_id),True)
   elif group=='L07':
    with pytest.raises(StorageError,match='SEMANTIC'):ledger.verify_source(replace(left,field_name='open'),binding)
  return
 if group.startswith('V'):
  v1=commit(db);before=db.manifest(v1)
  row2=record(observation_revision_id='revision-2',supersedes_revision_id='revision-1',value=Decimal('2.5'),known_from=K+timedelta(days=1))
  if group=='V03':assert commit(db)==v1;return
  if group=='V04':
   with pytest.raises(StorageError):commit(db,(row2,))
   return
  v2=commit(db,(row2,),'operation-2',v1)
  if group=='V01':assert query(db,v1).rows[0]['value']==Decimal('1.2500') and query(db,v2,known_at=K+timedelta(days=1)).rows[0]['value']==Decimal('2.5')
  elif group=='V02':assert db.manifest(v1)==before and db.verify(v1)['verified']
  elif group=='V05':
   db.select_version('control-dataset',v2,'control-new',K+timedelta(days=1));db.select_version('control-dataset',v1,'control-rollback',K+timedelta(days=2))
   assert db.selected_version('control-dataset')==v1 and query(db,v1).rows[0]['value']==Decimal('1.2500')
  return
 if group.startswith('M'):
  v=commit(db);m=db.manifest(v);file=tmp_path/'store'/m['file_entries'][0]['relative_path']
  if group=='M01':file.rename(file.with_suffix('.missing'))
  elif group=='M02':file.write_bytes(b'NON_MARKET_CORRUPT')
  elif group in {'M03','M04','M05'}:
   entry=dict(m['file_entries'][0]);entry[{'M03':'row_count','M04':'schema_fingerprint','M05':'relative_path'}[group]]={'M03':999,'M04':'0'*64,'M05':'../outside.parquet'}[group]
   with pytest.raises(StorageError):db.verify_file(entry)
   return
  elif group=='M06':
   (tmp_path/'store/objects/unreferenced.parquet').write_bytes(b'NOT_A_MEMBER')
   assert len(query(db,v).rows)==1;return
  with pytest.raises(StorageError):query(db,v)
  return
 if group.startswith('T'):
  v1=commit(db)
  phases={'T01':'during_file_write','T02':'after_install_before_catalog_commit','T03':'after_catalog_commit_before_acknowledgement','T04':'after_file_write_before_validation','T05':'during_catalog_transaction','T06':'after_validation_before_install'}
  phase=phases[group]
  def fault(at):
   if at==phase:
    if group=='T04':assert len(query(db,v1).rows)==1
    raise RuntimeError('CONTROLLED_FAULT')
  with pytest.raises(RuntimeError):commit(db,op='interrupted',parent=v1,hook=fault)
  db.close();db=database(tmp_path)
  assert len(query(db,v1).rows)==1
  if group=='T03':assert commit(db,op='interrupted',parent=v1)==db.operation_version('interrupted')
  else:assert db.operation_version('interrupted') is None
  assert isinstance(db.orphans(),dict)
  return
 if group.startswith('C'):
  v=commit(db);results=[];barrier=threading.Barrier(2)
  def writer(i):
   local=database(tmp_path)
   try:
    barrier.wait(timeout=10)
    results.append(commit(local,op='shared' if group=='C01' else 'race-'+str(i),parent=v,rows=(record(value=Decimal(i+1)),) if group=='C02' else None))
   except StorageError:results.append('REFUSED')
   finally:local.close()
  threads=[threading.Thread(target=writer,args=(i,)) for i in range(2)]
  for t in threads:t.start()
  if group=='C04':assert query(db,v).rows[0]['value']==Decimal('1.2500')
  for t in threads:t.join(15);assert not t.is_alive()
  assert len(results)==2
  if group=='C01':assert results[0]==results[1] and results[0]!='REFUSED'
  else:assert results.count('REFUSED')==1
  assert db.verify(v)['verified'];return
 if group.startswith('E'):
  v=commit(db)
  if group=='E01':assert schema.classify_change('canonical/v1','canonical/v2')=='BACKWARD_COMPATIBLE_ADDITION'
  elif group=='E02':
   with pytest.raises(StorageError):schema.get_schema('unknown')
  elif group=='E03':
   with pytest.raises(StorageError):schema.encode_decimal(Decimal('1e40'),'RAW')
  elif group=='E04':
   new=db.convert_version(v,'canonical/v2','convert-control')
   assert db.manifest(new)['parent_dataset_version_id']==v and query(db,new).rows[0]['value']==Decimal('1.2500') and db.verify(v)['verified']
  return
 if group.startswith('Q'):
  v=commit(db)
  if group=='Q01':
   with pytest.raises(StorageError,match='UNKNOWN_DATASET_VERSION'):query(db,'unknown')
  elif group=='Q02':
   q=query(db,v,known_at=K-timedelta(seconds=1));assert q.rows==() and q.excluded[0]['reason']=='FUTURE_INFORMATION'
  elif group=='Q03':
   with pytest.raises(StorageError,match='PRICE_BASIS'):query(db,v,price_basis='BACKWARD_ADJUSTED')
  elif group=='Q04':assert query(db,v,listing_ids=('other',)).rows==()
  elif group=='Q05':assert query(db,v).files_scanned==1 and query(db,v).files_verified==1
  elif group=='Q06':
   with pytest.raises(StorageError):query(db,v,maximum_rows=0)
  elif group=='Q07':assert [(r['observation_revision_id'],r['listing_id'],r['value']) for r in query(db,v).rows]==[('revision-1','00001',Decimal('1.2500'))]
  return
 if group.startswith('R'):
  refs=(('source_observation_revision','external-control','a'*64),)
  v1=commit(db,rows=(record(lineage=refs),));v2=commit(db,op='next',parent=v1,rows=(record(observation_revision_id='second',supersedes_revision_id='revision-1',lineage=refs,known_from=K+timedelta(days=1)),))
  out=db.impact('source_observation_revision','external-control',K+timedelta(days=2))
  assert set(out['dataset_versions'])=={v1,v2}
  if group=='R02':assert out['coverage_state']!='AUTHENTIC_COMPLETE'
  elif group=='R03':assert query(db,v1).rows[0]['observation_revision_id']=='revision-1'
  return
 if group.startswith('G'):
  row=record()
  if group=='G01':
   with pytest.raises(TypeError):replace(row,financial_eligibility=True)
  elif group=='G02':assert query(db,commit(db)).financial_eligible is False
  elif group=='G03':
   with pytest.raises(OSError):Path('/unmounted-original/CONTROL_ONLY').read_bytes()
  elif group=='G04':assert db.domain_registry()['review_revisions']=='TRANSACTIONAL_METADATA'

def test_legacy_partition_overwrite_reproduction(tmp_path,monkeypatch):
 import pandas as pd
 from omegadata.track_a.storage import ParquetStorage
 from omegadata.config import settings
 monkeypatch.setattr(settings,'parquet_root',str(tmp_path/'legacy'))
 store=ParquetStorage()
 a=store.store_daily('NON_MARKET_BOOKKEEPING',D,pd.DataFrame({'anonymous_sequence':[1]}))
 before=hashlib.sha256(a.path.read_bytes()).hexdigest()
 b=store.store_daily('NON_MARKET_BOOKKEEPING',D,pd.DataFrame({'anonymous_sequence':[2]}))
 assert a.path==b.path and before!=hashlib.sha256(b.path.read_bytes()).hexdigest()