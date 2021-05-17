import csv
import re
import os
from collections import defaultdict
from pathlib import Path

script_dir = os.path.dirname(__file__)

# this script was written by Captain Tux - https://github.com/CaptainTux
# the latest version will be available at https://github.com/AdamJCavanaugh/EndlessATCAirports

# this is parser for the CIFP, published by the FAA
# it provides SIDS and STARS for airports in the USA for EndlessATC
# it also generates routes to final, i.e., procedures where pilots navigate to final from an IAF
# the download of the current version is available here:
# https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/cifp/download/

# make sure to change this variable to point at the right folder
CIFP_FILENAME = 'CIFP/FAACIFP18'

# don't touch this
fieldnames = ['apt', 'id', 'transition', 'aob', 'fix', 'type', 'f_type', 'fix_type', 'index', 'name', 'lat', 'lon',
              'speed', 'alt_top', 'alt_min', 'alt_2', 'hdg']

# pretty self explanatory, apch_default_top_alt is used for approaches starting at an IAF, so not for STARS
star_default_top_alt = 14000
star_default_top_speed = 250
apch_default_top_alt = 6000
max_approach_alt = 2500
max_approach_speed = 220

entrypoints = {'HAARP': {'bearing': 330, 'alt': 6000, 'speed': 220},
               'KORRY': {'bearing': 220, 'alt': 8000, 'speed': 220},
               'BEUTY': {'bearing': 260, 'alt': 10000, 'speed': 220},
               'KARRS': {'bearing': 180, 'alt': 11000, 'speed': 250},
               'IGN': {'bearing': 360, 'alt': 14000, 'speed': 250},
               'HARTY': {'bearing': 270, 'alt': 14000, 'speed': 250},
               'CCC': {'bearing': 240, 'alt': 12000, 'speed': 250},
               'LOVES': {'bearing': 360, 'alt': 6000, 'speed': 220},
               'BRAND': {'bearing': 240, 'alt': 7000, 'speed': 220},
               'DYLIN': {'bearing': 200, 'alt': 8000, 'speed': 220},
               'FLOSI': {'bearing': 360, 'alt': 8000, 'speed': 220}
               }

# aircraft on an approach procedure will go no faster than alt_min_speeds[a] if the crossing restriction is aob a
alt_min_speeds = {7000: 220,
                  3000: 200
                  }

# specify final approach fixes with final altitude, speed and distance from the airport to intercept the ILS
# some final fixes on published charts might be too close to the airport
# in those cases aircraft might not be able to fly the approach in EATC, so you have to specify your own fixes
# often the last fix before the FAF should be sufficient (this is usually around 10 miles out)
final_app_fixes = {'ROSLY': {'final_length': 9.5, 'alt': 1800, 'speed': 200},
                   'ZETAL': {'final_length': 10, 'alt': 1800, 'speed': 200},
                   'AROKE': {'final_length': 10, 'alt': 1500, 'speed': 200},
                   'TELEX': {'final_length': 7.5, 'alt': 1500, 'speed': 180},
                   'CORVT': {'final_length': 9.6, 'alt': 2500, 'speed': 200},
                   'ZACHS': {'final_length': 10, 'alt': 1800, 'speed': 200},
                   'MALDE': {'final_length': 8.5, 'alt': 2500, 'speed': 200},
                   'GRENE': {'final_length': 10, 'alt': 1700, 'speed': 200},
                   'PAYMI': {'final_length': 8.5, 'alt': 1900, 'speed': 200},
                   'YOMAN': {'final_length': 10, 'alt': 1900, 'speed': 200},
                   'KILMA': {'final_length': 10, 'alt': 2000, 'speed': 200},
                   'EMBAY': {'final_length': 10, 'alt': 2000, 'speed': 200},
                   'GRITY': {'final_length': 10, 'alt': 2500, 'speed': 200},
                   'JARIT': {'final_length': 9.7, 'alt': 1600, 'speed': 200},
                   'GIMEE': {'final_length': 7.3, 'alt': 1500, 'speed': 180},
                   'AGNSS': {'final_length': 9.4, 'alt': 2500, 'speed': 200},
                   'RIVRA': {'final_length': 10, 'alt': 2500, 'speed': 200},
                   'CATOD': {'final_length': 10, 'alt': 3000, 'speed': 200},
                   'TICKL': {'final_length': 10, 'alt': 2000, 'speed': 200},
                   'QUENE': {'final_length': 10, 'alt': 1700, 'speed': 200},
                   'GEMKE': {'final_length': 8.5, 'alt': 1700, 'speed': 200}
                   }

# replace runway names with your own runway names
# the runway names will consist of the runway prefix (which is specified per airport below)
# followed by the runway name, which you can look up in ./cifp_out/apt_data/cifp_{icao}.csv
# look for the fields which have 'G' in the 'type' column
replace_runway_names = {'KJFK_RW04L': 'KJFK_04L_22R',
                        'KJFK_RW04R': 'KJFK_04R_22L',
                        'KJFK_RW22R': 'KJFK_04L_22R, rev',
                        'KJFK_RW22L': 'KJFK_04R_22L, rev',
                        'KJFK_RW13L': 'KJFK_13L_31R',
                        'KJFK_RW13R': 'KJFK_13R_31L',
                        'KJFK_RW31R': 'KJFK_13L_31R, rev',
                        'KJFK_RW31L': 'KJFK_13R_31L, rev',
                        'KLGA_RW04': 'KLGA_04_22',
                        'KLGA_RW22': 'KLGA_04_22, rev',
                        'KLGA_RW13': 'KLGA_13_31',
                        'KLGA_RW31': 'KLGA_13_31, rev',
                        'KEWR_RW04L': 'KEWR_04L_22R',
                        'KEWR_RW04R': 'KEWR_04R_22L',
                        'KEWR_RW22R': 'KEWR_04L_22R, rev',
                        'KEWR_RW22L': 'KEWR_04R_22L, rev',
                        'KEWR_RW11': 'KEWR_11_29',
                        'KEWR_RW29': 'KEWR_11_29, rev'
                        }


def parse_cifp():
    rows = []
    with open(CIFP_FILENAME, 'r') as f:
        lines = [line for line in f.readlines() if line[:5] in ['SUSAP', 'SUSAD'] or line[:10] == 'SUSAEAENRT']
        for line in lines:
            apt = line[6:10].strip() or 'VOR'
            if apt == 'ENRT':
                apt = 'RNAV_FIX'
            apt_id = line[13:19].strip()
            transition = line[19:25].strip()
            hdg = line[70:73]  # heading to fly when STAR terminates
            aob = line[82]
            fix = line[29:34].strip()
            entry_type = line[12]
            f_type = line[47:49]
            fix_type = line[26]
            sequence_index = line[26:29]
            name = line[93:123].strip()
            lat = f'{line[32:35]}.{line[35:37]}.{line[37:39]}.{line[39:41]}'
            lon = f'{line[41:45]}.{line[45:47]}.{line[47:49]}.{line[49:51]}'
            speed = line[99:102].strip()
            alt_top = line[84:89].strip()
            alt_min = line[89:94].strip()
            alt_2 = line[94:99].strip()
            rows.append({
                'apt': apt,
                'id': apt_id,
                'transition': transition,
                'aob': aob,
                'fix': fix,
                'type': entry_type,
                'f_type': f_type,
                'fix_type': fix_type,
                'index': sequence_index,
                'name': name,
                'lat': lat,
                'lon': lon,
                'speed': speed,
                'alt_top': alt_top,
                'alt_min': alt_min,
                'alt_2': alt_2,
                'hdg': hdg
            })
    with open('cifp_out/cifp_parsed.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_sids(lines, beacons, apt, runway_prefix='', start_index=0):
    runway_sids = defaultdict(lambda: defaultdict(lambda: []))
    for line in lines:
        if line['type'] == 'A':
            beacons[line['apt']] = line
        if line['type'] == 'C':
            beacons[line['id']] = line
    sid_lines = [line for line in lines if line['type'] == 'D']
    sid_list = defaultdict(lambda: [])

    for line in sid_lines:
        sid_list[line['id']].append(line)

    all_runways = [line['id'] for line in lines if line['type'] == 'G']

    for line in sid_lines:
        sid_id = line['id']
        transition = line['transition'][1:]
        if transition in all_runways:
            runway_sids[transition][sid_id].append(line)

    with open(f'cifp_out/{apt.lower()}/{apt}_sid_output.txt', 'w', newline='', encoding='utf8') as f:
        i = start_index
        used_fixes = []
        for runway, sids in runway_sids.items():
            i += 1
            f.write(f'\n\n{"#" * 50}\n'
                    f'[departure{i}]\n'
                    f'runway = {runway_prefix}{runway}\n')
            j = 0  # route counter
            for sid, route in sids.items():
                j += 1
                f.write(f'\nroute{j} = \n'
                        f'    {sid}.{route[-1]["fix"]}, {sid.split(".")[0]}\n')
                fix_name = ''
                for e in route:
                    if fix_name != e['fix'] and e['fix']:
                        fix_name = e['fix']
                        fix = beacons[fix_name]
                        used_fixes.append(fix_name)
                        f.write(f'    {fix["lat"]}, {fix["lon"]}\n'
                                f'# {fix_name}\n')

        f.write(f'\n\n{"#" * 50}\n'
                f'# BEACONS\n{"#" * 50}\n\n'
                f'beacons = \n')
        for name in sorted(set(used_fixes)):
            fix = beacons[name]
            f.write(f'    {fix["id"]}, {fix["lat"]}, {fix["lon"]}, {fix["name"].lower()}\n')
    return i


def write_stars(lines, beacons, apt, runway_prefix='', start_index=0):
    runway_stars = defaultdict(lambda: defaultdict(lambda: []))
    for line in lines:
        if line['type'] == 'A':
            beacons[line['apt']] = line
        if line['type'] == 'C':
            beacons[line['id']] = line
    star_lines = [line for line in lines if line['type'] == 'E']
    star_list = defaultdict(lambda: [])
    all_runways = [line['id'] for line in lines if line['type'] == 'G']

    for line in star_lines:
        star_list[line['id']].append(line)

    for star_id, s_lines in star_list.items():
        transitions = defaultdict(lambda: [])
        for line in s_lines:
            transitions[line['transition']].append(line)
        runways = [re.match(r'.?RW[0-9]{2}.?|.?ALL', t) for t in transitions.keys()]
        runways = [m.group(0)[1:] for m in runways if m]

        empty_trans_exists = False
        for transition, tlines in transitions.items():
            if transition[1:] in beacons.keys() or not transition[1:]:
                if not transition[1:]:
                    empty_trans_exists = True
                for runway in runways:
                    runway_stars[runway][f'{transition[1:] or tlines[0]["fix"]}.{star_id}'] += tlines
            elif transition[1:] in runways:
                for name, trans in runway_stars[transition[1:]].items():
                    if star_id in name:
                        trans += tlines
                if not empty_trans_exists:
                    runway_stars[transition[1:]][f'{tlines[0]["fix"]}.{star_id}'] += tlines

    with open(f'cifp_out/{apt.lower()}/{apt}_star_output.txt', 'w', newline='') as f:
        i = start_index
        used_fixes = []
        # get transition and first fix on route to calculate bearing for entrypoint in the end
        transitions = []
        entries = []
        for s_runway, stars in runway_stars.items():
            runway_list = all_runways if s_runway == 'ALL' else [s_runway]
            for runway in runway_list:
                for star, route in stars.items():
                    fix_name = ''
                    entry = None
                    for e in route:
                        if e['fix'] in entrypoints.keys() and not entry:
                            entry = e['fix']
                            entryname = f'{entry}.{star.split(".")[1]}'
                            if (entryname, runway) in transitions:
                                entry = None
                                break
                            transitions.append((entryname, runway))
                            entries.append(entry)
                            alt = entrypoints[entry]['alt'] or star_default_top_alt
                            speed = entrypoints[entry]['speed'] or star_default_top_speed
                            i += 1
                            runway_name = f'{runway_prefix}{runway}'
                            if runway_name in replace_runway_names.keys():
                                runway_name = replace_runway_names[runway_name]

                            f.write(f'\n\n{"#" * 50}\n'
                                    f'[approach{i}]\n'
                                    f'{"#" * 50}\n'
                                    f'# {entryname}\n'
                                    f'runway = {runway_name}\n'
                                    f'beacon = {entry}\n\n'
                                    f'route1 = \n'
                                    f'    {str(entrypoints[entry]["bearing"]).zfill(3)}\n')
                        if e['fix'] != fix_name and entry:
                            fix_name = e['fix']
                            fix = beacons[fix_name]
                            used_fixes.append(fix_name)
                            alt_top = e['alt_top']
                            alt_min = e['alt_min']
                            if e['speed']:
                                speed = e['speed']
                            if alt_min:
                                if 'FL' in alt_min:
                                    alt_min = int(alt_min[2:]) * 100
                                alt = min(alt, int(alt_min))
                            elif alt_top:
                                if 'FL' in alt_top:
                                    alt_top = int(alt_top[2:]) * 100
                                alt = min(alt, int(alt_top))
                            speed_alts = [a for a in alt_min_speeds.keys() if alt <= a]
                            if speed_alts:
                                speed = min(speed, alt_min_speeds[max(speed_alts)])

                            line = f'    {fix["lat"]}, {fix["lon"]}, {alt}, {speed} ; {e["fix"]}\n'
                            f.write(line)
                    if entry:
                        f.write(f'    end, {e["hdg"].strip() or "090"}')
                        # f.write(f'    99.9, {alt}, {speed} ; end\n\n')

        f.write(f'\n\n{"#" * 50}\n'
                f'# BEACONS\n{"#" * 50}\n\n'
                f'beacons = \n')
        for name in sorted(set(used_fixes)):
            fix = beacons[name]
            f.write(f'    {fix["id"]}, {fix["lat"]}, {fix["lon"]}, {fix["name"].lower()}\n')

        f.write(f'\n\n{"#" * 50}\n'
                f'# ENTRY POINTS\n{"#" * 50}\n\n'
                f'entrypoints = \n')
        for entrypoint in set(entries):
            bearing = entrypoints[entrypoint]['bearing']
            f.write(f'    {str(bearing).zfill(3)}, {entrypoint}\n')
    return i


def write_approaches(lines, beacons, apt, runway_prefix='', start_index=0):
    runway_approaches = defaultdict(lambda: defaultdict(lambda: []))
    for line in lines:
        if line['type'] == 'A':
            beacons[line['apt']] = line
        if line['type'] == 'C':
            beacons[line['id']] = line
    approach_lines = [line for line in lines if line['type'] == 'F']
    approach_list = defaultdict(lambda: [])

    for line in approach_lines:
        approach_list[line['id']].append(line)

    for approach_id, a_lines in approach_list.items():
        transitions = defaultdict(lambda: [])
        for line in a_lines:
            transitions[line['transition']].append(line)

        runway = f'{approach_id[1:]}'
        for transition, tlines in transitions.items():
            contains_valid_faf = [e['fix'] for e in tlines if e['fix'] in final_app_fixes.keys()]
            if contains_valid_faf:
                if transition[1:] in beacons.keys():
                    runway_approaches[runway][f'{transition[1:] or tlines[0]["fix"]}.{approach_id}'] += tlines
                # for name, trans in runway_approaches[runway].items():
                #     trans += tlines
                if not transition[1:]:
                    # final approach starts here
                    for t in runway_approaches[runway].keys():
                        runway_approaches[runway][t] += tlines
                    runway_approaches[runway][f'{tlines[0]["fix"]}.{approach_id}'] += tlines

    with open(f'cifp_out/{apt.lower()}/{apt}_approach_output.txt', 'w', newline='') as f:
        i = start_index
        used_fixes = []
        used_approaches = []
        for runway, approaches in runway_approaches.items():
            for approach, route in approaches.items():
                apch_string = ''
                iaf = approach.split('.')[0]
                # if not any(re.match(rf'{iaf}\..{runway}.?', a) for a in used_approaches):
                contains_valid_faf = [e['fix'] for e in route if e['fix'] in final_app_fixes.keys()]
                if any(contains_valid_faf):
                    used_approaches.append(approach)
                    i += 1
                    runway_name = f'{runway_prefix}RW{runway}'
                    replace_candidate = [v for r, v in replace_runway_names.items() if r in runway_name]
                    if replace_candidate:
                        runway_name = replace_candidate[0]

                    used_fixes.append(iaf)

                    apch_string += f'\n\n{"#" * 50}\n' \
                                   f'[approach{i}]\n' \
                                   f'{"#" * 50}\n' \
                                   f'# {approach}\n' \
                                   f'runway = {runway_name}\n' \
                                   f'beacon = {iaf}\n\n' \
                                   f'route1 = \n' \
                                   f'    360\n'
                    fix_name = ''
                    speed = 250
                    alt = apch_default_top_alt

                    entry = ''
                    faf = ''
                    app_string = ''
                    for e in route:
                        entry = e['fix']
                        if entry != fix_name and entry:
                            fix_name = entry
                            try:
                                fix = beacons[fix_name]
                            except KeyError:
                                break
                            # used_fixes.append(fix_name)
                            alt_top = e['alt_top']
                            alt_min = e['alt_min']
                            if not e['transition'][1:]:
                                speed = min(speed, max_approach_speed)
                                alt = min(alt, max_approach_alt)
                            if e['speed']:
                                speed = e['speed']
                            if alt_min:
                                if 'FL' in alt_min:
                                    alt_min = int(alt_min[2:]) * 100
                                alt = min(alt, int(alt_min))
                            elif alt_top:
                                if 'FL' in alt_top:
                                    alt_top = int(alt_top[2:]) * 100
                                alt = min(alt, int(alt_top))
                            speed_alts = [a for a in alt_min_speeds.keys() if int(alt) <= a]
                            if speed_alts:
                                speed = min(int(speed), alt_min_speeds[max(speed_alts)])
                            app_string += f'    {fix["lat"]}, {fix["lon"]}, {alt}, {speed} ; {e["fix"]}\n'
                            if entry in final_app_fixes.keys():
                                faf = entry
                                apch_string += app_string
                                app_string = ''

                    if faf:
                        apch_string += f'    {final_app_fixes[faf]["final_length"]}, {final_app_fixes[faf]["alt"]}, '\
                                       f'{final_app_fixes[faf]["speed"]} ; end\n'
                        f.write(apch_string)

        f.write(f'\n\n{"#" * 50}\n'
                f'# BEACONS\n{"#" * 50}\n\n'
                f'beacons = \n')
        for name in sorted(set(used_fixes)):
            fix = beacons[name]
            f.write(f'    {fix["id"]}, {fix["lat"]}, {fix["lon"]}, {fix["name"].lower()}\n')
    return i


def write_apt_data(apt):
    with open('cifp_out/cifp_parsed.csv', 'r') as f:
        reader = csv.DictReader(f)
        lines = list(reader)
    with open(f'cifp_out/apt_data/cifp_{apt.lower()}.csv', 'w', newline='') as fo:
        writer = csv.DictWriter(fo, fieldnames=fieldnames)
        writer.writeheader()
        wlines = [line for line in lines if line['apt'] == apt]
        wlines += [line for line in lines if line['apt'] in ['RNAV_FIX', 'VOR']]
        writer.writerows(wlines)


def write_fix_coords():
    with open('cifp_out/cifp_parsed.csv', 'r') as f:
        reader = csv.DictReader(f)
        lines = list(reader)
    with open(f'cifp_out/cifp_coords.csv', 'w', newline='') as fo:
        writer = csv.DictWriter(fo, fieldnames=fieldnames)
        writer.writeheader()
        wlines = [line for line in lines if line['apt'] in ['RNAV_FIX', 'VOR']]
        writer.writerows(wlines)


def parse_approaches(apt, start_index=0):
    i = app_start_index
    write_apt_data(apt)
    with open(f'cifp_out/apt_data/cifp_{apt.lower()}.csv', 'r') as f:
        reader = csv.DictReader(f)
        lines = list(reader)
    with open('cifp_out/cifp_coords.csv', 'r') as f:
        beacon_list = list(csv.DictReader(f))

    beacons = {line['id']: line for line in beacon_list if
               line['apt'] == 'RNAV_FIX' or line['apt'] == 'VOR'}
    runway_prefix = f'{apt}_'
    i = write_stars(lines, beacons, apt.lower(), runway_prefix=runway_prefix, start_index=i)
    i = write_approaches(lines, beacons, apt.lower(), runway_prefix=runway_prefix, start_index=i)
    # write_sids(apt, lines, beacons, apt.lower(), runway_prefix=runway_prefix)
    return i


def parse_sids(apt, start_index=0):
    i = start_index
    write_apt_data(apt)
    with open(f'cifp_out/apt_data/cifp_{apt.lower()}.csv', 'r') as f:
        reader = csv.DictReader(f)
        lines = list(reader)
    with open('cifp_out/cifp_coords.csv', 'r') as f:
        beacon_list = list(csv.DictReader(f))

    beacons = {line['id']: line for line in beacon_list if
               line['apt'] == 'RNAV_FIX' or line['apt'] == 'VOR'}
    runway_prefix = f'{apt}_'
    i = write_sids(lines, beacons, apt.lower(), runway_prefix=runway_prefix, start_index=i)
    return i

# you only need to run the parse_cifp() function once, it parses the CIFP data to a better format, used in this script
# same thing for write_fix_coords() - note: has to run AFTER the parse_cifp() function


if __name__ == '__main__':
    Path('cifp_out/apt_data').mkdir(parents=True, exist_ok=True)
    parse_cifp()
    write_fix_coords()
    airports = ['KJFK', 'KLGA', 'KEWR']
    app_start_index = 0  # for approach numbering
    sid_start_index = 0  # for sid numbering
    for airport in airports:
        # make sure the output folder for each airport exists
        Path(f'cifp_out/{airport.lower()}').mkdir(parents=True, exist_ok=True)
        app_start_index = parse_approaches(airport, app_start_index)
        sid_start_index = parse_sids(airport, sid_start_index)
    pass
