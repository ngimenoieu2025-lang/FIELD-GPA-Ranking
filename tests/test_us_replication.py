"""Small numerical checks; no raw US data needed."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from us_replication import section_gpa, aggregate, compare, resolve_department_codes
from us_model import field_effects
from us_mapping import classify, SPANISH_TO_AREA

class USReplicationTests(unittest.TestCase):
    def test_numeric_grades_only(self):
        d = pd.DataFrame({'A': [50, 0, 0, -1, 90], 'B': [25, 0, 0, 0, 90],
                          'F': [0, 0, 100, 0, 0], 'Pass': [0, 100, 0, 0, 0], 'W': [25, 0, 0, 0, 0]})
        g, _ = section_gpa(d)
        self.assertAlmostEqual(g.iloc[0], 11/3)
        self.assertTrue(np.isnan(g.iloc[1]))
        self.assertEqual(g.iloc[2], 0)
        self.assertTrue(g.iloc[3:].isna().all())
        self.assertEqual(section_gpa(pd.DataFrame({'A+':[100]}))[0].iloc[0], 4.3)
        self.assertEqual(section_gpa(pd.DataFrame({'A+':[100]}), 4)[0].iloc[0], 4)

    def test_enrollment_weighting(self):
        d = pd.DataFrame({'univ':['u']*3, 'field':['f']*3, 'year':[2020]*3,
                          'gpa':[4.,2.,1.], 'enrollment':[10,30,np.nan],
                          'valid_gpa':[True]*3,'mapped':[True]*3,'valid_weight':[True,True,False]})
        self.assertAlmostEqual(aggregate(d)['mean'].iloc[0], 2.5)
        self.assertAlmostEqual(aggregate(d,False)['mean'].iloc[0], 7/3)

    def test_missing_codes_use_unambiguous_names(self):
        m=pd.DataFrame({'department_name':['Anatomy','Duplicate','Duplicate'], 'department_code':['ANA','D1','D2']})
        d=pd.DataFrame({'Department_Code':[np.nan,np.nan,'KNOWN'], 'Department_Name':['Anatomy','Duplicate','Anatomy']})
        self.assertEqual(resolve_department_codes(d,m).tolist(),['ANA','','KNOWN'])

    def test_mapping_and_exclusions(self):
        self.assertEqual(len(SPANISH_TO_AREA),29)
        self.assertEqual(classify('Teacher Education','Public and Social Services')[0],'Education')
        self.assertEqual(classify('Economics','Social Sciences')[0],'Social sciences & law')
        self.assertEqual(classify('Computer Science','Non-engineering Sciences and Mathematics')[0],'Science, mathematics & computing')
        self.assertEqual(classify('Honors','Uncategorized')[0],'')

    def test_sum_coded_model_and_comparison(self):
        rng=np.random.default_rng(42)
        d=pd.DataFrame([{'univ':f'u{u}','year':2010+y,'field':f,'mean':3+u*.2+y*.1+effect+rng.normal(0,.01)}
                        for u in range(5) for y in range(3) for f,effect in [('a',-.4),('b',.1),('c',.3)]])
        d=d.drop(index=[2,7,18])  # unbalanced cells
        e,_=field_effects(d)
        self.assertAlmostEqual(e.effect.sum(),0.,places=12)
        for f,expected in [('a',-.4),('b',.1),('c',.3)]:
            self.assertAlmostEqual(e.loc[f,'effect'],expected,delta=.02)
        # Independent reference: treatment coding, then recenter its coefficients.
        x=pd.get_dummies(d[['field','univ','year']].astype(str),drop_first=True,dtype=float)
        x.insert(0,'intercept',1.)
        beta=pd.Series(np.linalg.lstsq(x,d['mean'],rcond=None)[0],index=x.columns)
        ref=np.array([0.,beta.field_b,beta.field_c]);ref-=ref.mean()
        np.testing.assert_allclose(e.sort_index().effect,ref,atol=1e-12)
        scaled=d.copy();scaled['mean']=2*d['mean']+4
        _,stats=compare(d,scaled)
        self.assertAlmostEqual(stats['pearson_r'],1.)
        self.assertAlmostEqual(stats['spearman_rho'],1.)

    def test_disconnected_model_rejected(self):
        d=pd.DataFrame({'univ':['a','a','b','b'],'year':[2020]*4,'field':['x','x','y','y'],'mean':[1.,2.,3.,4.]})
        with self.assertRaises(ValueError): field_effects(d)

if __name__=='__main__': unittest.main()
