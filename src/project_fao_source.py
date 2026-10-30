"""Qualify the separately planned FAO source without running scenarios."""

import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE_M49 = {
    'Argentina': '032', 'Australia': '036', 'Bulgaria': '100',
    'Canada': '124', 'Egypt': '818', 'France': '250',
    'Kazakhstan': '398', 'Morocco': '504', 'Romania': '642',
    'Russian Federation': '643', 'Tunisia': '788', 'Ukraine': '804',
    'United States of America': '840',
}
FLAGS = {'A': 'Official value', 'I': 'Value imputed by a receiving agency'}
FIELDS = [
    'source_file', 'source_row', 'domain', 'reporter_fao', 'reporter_name',
    'reporter_m49', 'partner_fao', 'partner_name', 'partner_m49',
    'element_code', 'element', 'item_cpc', 'item', 'year', 'unit',
    'value_tonnes', 'kg_fraction', 'flag', 'flag_description', 'state',
]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def positive(row):
    return row is not None and row['state'] == 'positive'


def percent(value):
    with localcontext() as ctx:
        ctx.prec = 60
        return format(Decimal(value.numerator * 100) / Decimal(value.denominator), '.6f')


def project(originals, output):
    plan = json.loads((ROOT / 'data/planned_fao_network.json').read_text(encoding='utf-8'))
    by_name = {a['name']: a for a in plan['importers'] + plan['origins']}
    rows, captures, lookup = [], [], {}
    for request in plan['downloads']:
        name = request['id']
        path = originals / (name + '.csv')
        content = path.read_bytes()
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
        native = list(reader)
        assert len(native) == request['maximum_observations'], (name, len(native))
        bilateral = request['domain'] == 'TM'
        reporter_group = request.get('reporters', request.get('areas'))
        reporters = {a['name'] for a in plan[reporter_group]}
        partners = {a['name'] for a in plan[request['partners']]} if bilateral else {''}
        expected = {(r, p, str(y)) for r in reporters for p in partners for y in request['years']}
        observed = set()
        element_code = '5610' if request['element'] == 'Import Quantity' else '5910'
        for number, source in enumerate(native, 2):
            reporter_name = source['Reporter Countries'] if bilateral else source['Area']
            partner_name = source['Partner Countries'] if bilateral else ''
            reporter_m49 = source['Reporter Country Code (M49)'] if bilateral else source['Area Code (M49)']
            partner_m49 = source['Partner Country Code (M49)'] if bilateral else ''
            key = (reporter_name, partner_name, source['Year'])
            assert key in expected and key not in observed, (name, key)
            observed.add(key)
            assert source['Domain Code'] == request['domain']
            assert source['Item Code (CPC)'] == '0111' and source['Item'] == 'Wheat'
            assert source['Element Code'] == element_code
            assert source['Element'].lower() == request['element'].lower()
            assert source['Year'] == source['Year Code']
            assert reporter_m49 == NATIVE_M49[reporter_name]
            assert not bilateral or partner_m49 == NATIVE_M49[partner_name]
            assert not source.get('Note', '')
            token = source['Value']
            quantity, state = '', 'missing'
            if token:
                value = Decimal(token)
                assert value.is_finite() and source['Unit'] == 't'
                assert FLAGS.get(source['Flag']) == source['Flag Description']
                quantity = str(Fraction(value) * 1000)
                state = 'positive' if value > 0 else ('zero' if value == 0 else 'negative')
            else:
                assert not source['Unit'] and not source['Flag'] and not source['Flag Description']
            row = dict(zip(FIELDS, [
                name + '.csv', number, request['domain'], by_name[reporter_name]['code'], reporter_name,
                reporter_m49, by_name[partner_name]['code'] if bilateral else '', partner_name, partner_m49,
                source['Element Code'], source['Element'], source['Item Code (CPC)'], source['Item'],
                source['Year'], source['Unit'], token, quantity, source['Flag'], source['Flag Description'], state,
            ]))
            rows.append(row)
            lookup[(name, row['reporter_fao'], row['partner_fao'], int(row['year']))] = row
        assert observed == expected
        captures.append({'id': name, 'domain': request['domain'], 'rows': len(native),
                         'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                         'source_url': 'https://www.fao.org/faostat/en/#data/' + request['domain']})
    assert len(rows) == 179

    failures, totals, common, routes = [], [], [], []
    for request_id, group, years in [
        ('world_imports', plan['importers'], [2018, 2019, 2020]),
        ('prior_world_exports', plan['origins'], [2018, 2019]),
    ]:
        for area in group:
            for year in years:
                row = lookup[(request_id, area['code'], '', year)]
                valid = positive(row)
                totals.append({'kind': request_id, 'area_fao': area['code'], 'name': area['name'],
                               'year': year, 'state': row['state'], 'flag': row['flag'], 'pass': valid})
                if not valid:
                    failures.append(f'{request_id}:{area["code"]}:{year}:positive_unique_total')
    for importer in plan['importers']:
        i = importer['code']
        for year in [2019, 2020]:
            eligible = [o for o in plan['origins']
                        if positive(lookup.get(('import_pairs', i, o['code'], year)))
                        and positive(lookup.get(('export_mirrors', o['code'], i, year)))]
            mass = sum((Fraction(lookup[('import_pairs', i, o['code'], year)]['kg_fraction'])
                        for o in eligible), Fraction())
            world = lookup[('world_imports', i, '', year)]
            ratio = mass / Fraction(world['kg_fraction']) if positive(world) else None
            coverage_ok = ratio is not None and Fraction(4, 5) <= ratio <= Fraction(21, 20)
            origin_ok = len(eligible) >= 2
            common.append({'importer_fao': i, 'name': importer['name'], 'year': year,
                           'common_origins': [o['code'] for o in eligible],
                           'common_origin_count': len(eligible), 'common_import_kg_fraction': str(mass),
                           'world_import_kg_fraction': world['kg_fraction'],
                           'coverage_fraction': str(ratio) if ratio is not None else None,
                           'coverage_percent_approx': percent(ratio) if ratio is not None else None,
                           'coverage_pass': coverage_ok, 'origin_count_pass': origin_ok})
            if not coverage_ok:
                failures.append(f'common_support:{i}:{year}:coverage_80_to_105_percent')
            if not origin_ok:
                failures.append(f'common_support:{i}:{year}:at_least_two_origins')
            prior = [o['code'] for o in plan['origins']
                     if positive(lookup.get(('import_pairs', i, o['code'], year - 1)))]
            prior_ok = len(prior) >= 2
            routes.append({'importer_fao': i, 'name': importer['name'], 'target_year': year,
                           'prior_year': year - 1, 'origins': prior, 'count': len(prior), 'pass': prior_ok})
            if not prior_ok:
                failures.append(f'prior_routes:{i}:{year}:at_least_two_origins')

    output.mkdir(parents=True, exist_ok=False)
    with (output / 'source_projection.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    dump(output / 'source_receipt.json', {
        'status': 'PASS_NATIVE_SCHEMA_AND_FIXED_KEYS', 'observations': len(rows), 'captures': captures,
        'capture_protocol_commit': 'cc5d95dbabefb329d0d7d737c0183c1e474a83dc',
        'mechanism': 'Four ordinary public website filtered CSV downloads; original files retained privately',
        'http_status_and_response_headers': 'unavailable from browser file download; no status inferred',
        'download_event_limitation': 'First tool event timed out although the browser saved the CSV; verified on disk, no source retry',
        'native_code_binding': 'UI quantity codes 2610/2910 export as 5610/5910; country output M49, item output CPC; source-specific FAO crosswalk retained',
        'source_update_dates': {'TM': '2025-12-23', 'TCL': '2026-07-24'},
        'value_state_counts': {s: sum(r['state'] == s for r in rows) for s in ['positive', 'zero', 'negative', 'missing']},
        'positive_imputed_values': sum(r['state'] == 'positive' and r['flag'] == 'I' for r in rows),
        'source_license_scope': 'FAO CC BY 4.0 with upstream exceptions; free attributed bounded publication only; source facts not relicensed by code license',
    })
    dump(output / 'input_gate.json', {
        'status': 'PASS_SOURCE_QUALIFICATION' if not failures else 'FAIL_SOURCE_QUALIFICATION',
        'national_totals': totals, 'common_support': common, 'prior_routes': routes,
        'failed_gates': failures, 'scenario_outputs_computed': False,
        'thresholds': {'minimum_coverage': '4/5', 'maximum_coverage': '21/20', 'minimum_origins': 2, 'minimum_prior_routes': 2},
        'scope': 'FAO source basis only; earlier UN source failure unchanged',
    })
    print(json.dumps({'status': 'PASS_SOURCE_QUALIFICATION' if not failures else 'FAIL_SOURCE_QUALIFICATION',
                      'observations': len(rows), 'failed_gates': failures,
                      'coverage': [{k: x[k] for k in ['name', 'year', 'common_origin_count', 'coverage_percent_approx', 'coverage_pass']} for x in common]}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    project(args.originals, args.out)
