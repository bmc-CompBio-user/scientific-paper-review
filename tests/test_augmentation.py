import copy
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('augment_sources',Path(__file__).resolve().parents[1]/'examples/augment_sources.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class SourceExpansionTests(unittest.TestCase):
 def setUp(self):
  self.old={'documents':[{'id':'main','sha256':'original'}], 'pages':[{'id':'main.p001','blocks':[{'text':'Original'}],'images':[{'sha256':'image'}]}]}
  self.current=copy.deepcopy(self.old)
  self.current['documents'].append({'id':'supp','sha256':'supplement'})
  self.current['pages'].append({'id':'supp.p001','blocks':[],'images':[]})
 def test_preserves_source_context_and_detects_new_document(self):
  self.assertEqual(module.unchanged_prior_pages(self.old,self.current),{'main.p001'})
  self.assertEqual(len(self.current['pages'])-len(self.old['pages']),1)
 def test_changed_main_source_rejected(self):
  self.current['documents'][0]['sha256']='changed'
  with self.assertRaisesRegex(ValueError,'removed or changed'):module.unchanged_prior_pages(self.old,self.current)
 def test_changed_main_render_rejected(self):
  self.current['pages'][0]['images'][0]['sha256']='changed'
  with self.assertRaisesRegex(ValueError,'representation changed'):module.unchanged_prior_pages(self.old,self.current)
 def test_removed_main_rejected(self):
  self.current['documents']=self.current['documents'][1:]
  with self.assertRaisesRegex(ValueError,'removed or changed'):module.unchanged_prior_pages(self.old,self.current)
if __name__=='__main__':unittest.main()
