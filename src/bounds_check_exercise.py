"""Independently reconstruct both-year summary and every exercise response."""
from pathlib import Path
from fractions import Fraction as F
import csv,json
ROOT=Path(__file__).resolve().parents[1]
def read(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def main():
    n=0
    def ck(v,s):
        nonlocal n
        assert v,s;n+=1
    rows=[r for y in [2019,2020] for r in read(ROOT/('results/bounds/endpoints_'+str(y)+'.csv'))];summary=json.loads((ROOT/'results/bounds/summary.json').read_bytes())
    ck(len(rows)==1440 and len({r['case_id'] for r in rows})==480,'all base and endpoint accounts');ck(summary['maximum_interval_illustration']==max(rows,key=lambda r:F(r['interval_width_kg'])),'actual declared maximum and first-tie order')
    classes=['ZERO_MODELED_LOSS','KNOWN_NETWORK_SUFFICIENT','CONDITIONAL_SHORTFALL','UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY'];expected=[]
    for y in [2019,2020]:
        for basis in ['import','mirror']:
            for gamma in ['0','1/2','1']:
                rs=[r for r in rows if (r['year'],r['basis'],r['gamma'])==(str(y),basis,gamma)]
                expected.append(dict(year=y,basis=basis,gamma=gamma,cases=len(rs),positive_loss_cases=sum(F(r['demand_kg'])>0 for r in rs),classifications={k:sum(r['classification']==k for r in rs) for k in classes},positive_overclaim_cases=sum(F(r['shared_overclaim_kg'])>0 for r in rs),max_overclaim_kg=str(max(F(r['shared_overclaim_kg']) for r in rs)),max_interval_width_kg=str(max(F(r['interval_width_kg']) for r in rs))))
    ck(summary['groups']==expected,'all twelve complete classification groups')
    source=read(ROOT/'data/fao/source_projection.csv')
    ck((summary['source_positions'],summary['positive_source_positions'],summary['missing_source_positions'],summary['positive_imputed_positions'])==(len(source),sum(r['state']=='positive' for r in source),sum(r['state']=='missing' for r in source),sum(r['state']=='positive' and r['flag']=='I' for r in source)),'source state/flag totals')
    ck(summary['original_FAO_gate']=='FAIL_SOURCE_QUALIFICATION' and summary['original_coverage_gated_scenarios']=='UNEXECUTED','original scope remains held')
    ck((summary['base_cases'],summary['endpoint_evaluations'],summary['cut_subsets'])==(480,1440,11520),'complete finite summary counts')
    requests=json.loads((ROOT/'data/bounds_requests.json').read_bytes());answers=json.loads((ROOT/'results/bounds/exercise.json').read_bytes());ck(len(requests)==len(answers)==8,'all fixed requests')
    for r,a in zip(requests,answers):
        ck(a['request']==r,'original exercise input');keys={'scope','year','basis','alpha','beta','lost_origin','gamma'}
        if set(r)-keys:status='REJECT'
        elif set(r)!=keys:status='ABSTAIN'
        elif r['scope']!='conditional_replacement_interval':status='REJECT'
        elif r['year'] not in [2019,2020]:status='ABSTAIN'
        else:
            matches=[x for x in rows if all(str(r[k])==x[k] for k in ['year','basis','alpha','beta','lost_origin','gamma'])];status='QUALIFIED_INTERVAL' if len(matches)==1 else 'ABSTAIN'
        ck(a['response']['status']==status,'defensive response status')
        if status=='QUALIFIED_INTERVAL':
            x=matches[0]
            for out,field in [('demand_kg','demand_kg'),('lower_covered_kg','known_covered_kg'),('upper_covered_kg','endpoint_covered_kg'),('lower_unmet_kg','lower_unmet_kg'),('upper_unmet_kg','upper_unmet_kg'),('unrestricted_upper_covered_kg','demand_kg')]:ck(F(a['response'][out])==F(x[field]),'exact qualified interval')
            ck(a['response']['classification']==x['classification'],'qualified classification')
    result=dict(status='PASS',independent_conditions=n,requests=8,qualified_intervals=2,abstentions=2,rejections=4,summary_groups=12)
    (ROOT/'results/bounds/SUMMARY_EXERCISE_CHECK.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(result)
if __name__=='__main__':main()
