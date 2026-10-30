"""Reconcile native CSVs and qualification with independent SQLite/Decimal checks."""

import argparse
import csv
import hashlib
import io
import json
import sqlite3
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 70
ROOT = Path(__file__).resolve().parents[1]


def verify(originals, projection):
    checks = 0

    def check(condition, label):
        nonlocal checks
        checks += 1
        if not condition:
            raise AssertionError(label)

    def rational_decimal(value):
        if '/' in value:
            n, d = value.split('/')
            return Decimal(n) / Decimal(d)
        return Decimal(value)

    class DecimalSum:
        def __init__(self):
            self.value = Decimal(0)

        def step(self, value):
            self.value += Decimal(value)

        def finalize(self):
            return str(self.value)

    db = sqlite3.connect(':memory:')
    db.create_aggregate('decimal_sum', 1, DecimalSum)
    db.execute('create table native(kind text, reporter text, partner text, year integer, value text, positive integer)')
    plan = json.loads((ROOT / 'data/planned_fao_network.json').read_text(encoding='utf-8'))
    codes = {a['name']: a['code'] for a in plan['importers'] + plan['origins']}
    source_receipt = json.loads((projection / 'source_receipt.json').read_text(encoding='utf-8'))
    source_hashes = {c['id']: c for c in source_receipt['captures']}
    with (projection / 'source_projection.csv').open(encoding='utf-8', newline='') as handle:
        public_rows = list(csv.DictReader(handle))
    public = {(r['source_file'], int(r['source_row'])): r for r in public_rows}
    check(len(public) == len(public_rows) == 179, 'projection full keys')
    originals_hashes = {}
    for request in plan['downloads']:
        name = request['id']
        content = (originals / (name + '.csv')).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        originals_hashes[name] = digest
        check(digest == source_hashes[name]['sha256'], name + ' original hash')
        check(len(content) == source_hashes[name]['bytes'], name + ' native bytes')
        native = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline='')))
        check(len(native) == request['maximum_observations'] == source_hashes[name]['rows'], name + ' native row count')
        bilateral = request['domain'] == 'TM'
        reporter_names = {a['name'] for a in plan[request.get('reporters', request.get('areas'))]}
        partner_names = {a['name'] for a in plan[request['partners']]} if bilateral else {''}
        expected_keys = {(r, p, str(y)) for r in reporter_names for p in partner_names for y in request['years']}
        actual_keys = set()
        for number, row in enumerate(native, 2):
            projected = public[(name + '.csv', number)]
            reporter = row['Reporter Countries'] if bilateral else row['Area']
            partner = row['Partner Countries'] if bilateral else ''
            reporter_m49 = row['Reporter Country Code (M49)'] if bilateral else row['Area Code (M49)']
            partner_m49 = row['Partner Country Code (M49)'] if bilateral else ''
            actual_keys.add((reporter, partner, row['Year']))
            check(row['Domain Code'] == request['domain'], 'planned native domain')
            check(row['Element'].lower() == request['element'].lower(), 'planned native quantity element')
            check(row['Element Code'] == ('5610' if request['element'] == 'Import Quantity' else '5910'), 'native quantity code')
            expected_fields = {
                'domain': row['Domain Code'], 'reporter_name': reporter, 'partner_name': partner,
                'reporter_fao': codes[reporter], 'partner_fao': codes[partner] if bilateral else '',
                'reporter_m49': reporter_m49, 'partner_m49': partner_m49,
                'element_code': row['Element Code'], 'element': row['Element'],
                'item_cpc': row['Item Code (CPC)'], 'item': row['Item'],
                'year': row['Year'], 'unit': row['Unit'], 'value_tonnes': row['Value'],
                'flag': row['Flag'], 'flag_description': row['Flag Description'],
            }
            for key, value in expected_fields.items():
                check(projected[key] == value, f'{name}:{number}:{key}')
            check(row['Year'] == row['Year Code'], 'native year identity')
            check(row['Item'] == 'Wheat' and row['Item Code (CPC)'] == '0111', 'native grain identity')
            check(not row.get('Note'), 'no additional native note silently discarded')
            token = row['Value']
            if token:
                value = Decimal(token)
                check(value.is_finite() and row['Unit'] == 't', 'native finite tonnes')
                check((row['Flag'], row['Flag Description']) in {
                    ('A', 'Official value'), ('I', 'Value imputed by a receiving agency')}, 'native flag binding')
                state = 'positive' if value > 0 else ('zero' if value == 0 else 'negative')
                check(rational_decimal(projected['kg_fraction']) == value * 1000, 'independent decimal kg conversion')
            else:
                value, state = Decimal(0), 'missing'
                check(not projected['kg_fraction'] and not row['Unit'] and not row['Flag'], 'native missing is not zero')
            check(projected['state'] == state, 'native state projection')
            db.execute('insert into native values (?,?,?,?,?,?)',
                       (name, codes[reporter], codes[partner] if bilateral else '',
                        int(row['Year']), str(value), int(state == 'positive')))
        check(actual_keys == expected_keys, 'independent complete fixed cohort')
        check(not db.execute('select 1 from native where kind=? group by reporter,partner,year having count(*)<>1', (name,)).fetchall(), 'native unique full cohort keys')

    gate = json.loads((projection / 'input_gate.json').read_text(encoding='utf-8'))
    failures = []
    for row in gate['national_totals']:
        native = db.execute('select value,positive from native where kind=? and reporter=? and partner=\'\' and year=?',
                            (row['kind'], row['area_fao'], row['year'])).fetchall()
        check(len(native) == 1, 'national total uniqueness')
        valid = bool(native[0][1])
        check(row['pass'] == valid, 'national total gate')
        if not valid:
            failures.append(f'{row["kind"]}:{row["area_fao"]}:{row["year"]}:positive_unique_total')
    for row in gate['common_support']:
        pairs = db.execute('''select i.partner,i.value from native i join native x
            on x.kind='export_mirrors' and x.reporter=i.partner and x.partner=i.reporter and x.year=i.year
            where i.kind='import_pairs' and i.reporter=? and i.year=? and i.positive=1 and x.positive=1
            order by cast(i.partner as integer)''', (row['importer_fao'], row['year'])).fetchall()
        mass = sum((Decimal(value) for _, value in pairs), Decimal(0))
        world = db.execute('select value,positive from native where kind=\'world_imports\' and reporter=? and year=?',
                           (row['importer_fao'], row['year'])).fetchone()
        ratio = mass / Decimal(world[0]) if world[1] else None
        coverage_ok = ratio is not None and Decimal('.8') <= ratio <= Decimal('1.05')
        origins_ok = len(pairs) >= 2
        check(row['common_origins'] == [p[0] for p in pairs], 'SQL common-support membership')
        check(row['common_origin_count'] == len(pairs), 'SQL common-origin count')
        check(rational_decimal(row['common_import_kg_fraction']) == mass * 1000, 'SQL Decimal common mass')
        check(rational_decimal(row['world_import_kg_fraction']) == Decimal(world[0]) * 1000, 'native national denominator')
        check(rational_decimal(row['coverage_fraction']) == ratio, 'independent coverage ratio')
        check(row['coverage_pass'] == coverage_ok and row['origin_count_pass'] == origins_ok, 'unrounded fixed support gates')
        if not coverage_ok:
            failures.append(f'common_support:{row["importer_fao"]}:{row["year"]}:coverage_80_to_105_percent')
        if not origins_ok:
            failures.append(f'common_support:{row["importer_fao"]}:{row["year"]}:at_least_two_origins')
    for row in gate['prior_routes']:
        count, mass = db.execute('select count(*),decimal_sum(value) from native where kind=\'import_pairs\' and reporter=? and year=? and positive=1',
                                (row['importer_fao'], row['prior_year'])).fetchone()
        valid = count >= 2
        check(row['count'] == count and row['pass'] == valid, 'SQL prior-route gate')
        check(Decimal(mass) > 0, 'positive prior-route mass')
        if not valid:
            failures.append(f'prior_routes:{row["importer_fao"]}:{row["target_year"]}:at_least_two_origins')
    check(sorted(failures) == sorted(gate['failed_gates']), 'all native failed gates retained')
    check(gate['status'] == ('FAIL_SOURCE_QUALIFICATION' if failures else 'PASS_SOURCE_QUALIFICATION'), 'native source status')
    check(gate['scenario_outputs_computed'] is False, 'no scenario claim at source qualification')
    result = {'status': 'PASS_INDEPENDENT_SOURCE_GATE_RECONCILIATION', 'conditions': checks,
              'method': 'Native CSV fields, independent SQLite joins and 70-digit Decimal arithmetic; no projector helper imports',
              'original_hashes': originals_hashes, 'source_qualification': gate['status'], 'failed_gates': failures,
              'projection_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(projection.iterdir()) if p.name != 'source_verification.json'}}
    (projection / 'source_verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'conditions': checks, 'source_qualification': gate['status'], 'failed_gates': failures}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--projection', type=Path, required=True)
    args = parser.parse_args()
    verify(args.originals, args.projection)
