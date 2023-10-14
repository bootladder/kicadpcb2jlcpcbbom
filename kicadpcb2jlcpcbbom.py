#!/usr/bin/python
import csv
import sexpdata
import sys
def parse_kicad_pcb_file(file_path):
    with open(file_path, 'r') as file:
        pcb_content = file.read()
    try:
        parsed_data = sexpdata.loads(pcb_content)
        return parsed_data
    except Exception as e:
        print(f"Error parsing .kicad_pcb file: {str(e)}")
        return None

def strip_symbol(symbol):
    if isinstance(symbol, sexpdata.Symbol):
        return symbol.value()
    else:
        return symbol

def strip_symbols(parsed_data):
    if isinstance(parsed_data, list):
        return [strip_symbols(item) for item in parsed_data]
    elif isinstance(parsed_data, tuple):
        return tuple(strip_symbols(item) for item in parsed_data)
    elif isinstance(parsed_data, sexpdata.Symbol):
        return strip_symbol(parsed_data)
    else:
        return parsed_data

def extract_bom_items_from_pcb_list(pcb_data):
    bom_items = []
    for item in pcb_data:
        if isinstance(item, list) and item[0] == 'footprint':
            footprint_name = item[1]
            refdes, value = None, None
            for prop in item[2:]:
                if isinstance(prop, list) and prop[0] == 'fp_text':
                    prop_type, text = prop[1], prop[2]
                    if prop_type == 'reference':
                        refdes = text
                    elif prop_type == 'value':
                        value = text
            if refdes is not None and value is not None:
                bom_items.append({'footprint': footprint_name, 'refdes': refdes, 'value': value, 'part': 'PART'})
    return bom_items

def bom_items_to_csv(bom_items):
    grouped_bom = {}
    csv_data = []

    for item in bom_items:
        key = (item['value'], item['footprint'])
        existing_entry = grouped_bom.get(key)
        if existing_entry:
            existing_entry['refdes'].append(item['refdes'])
        else:
            grouped_bom[key] = {'value': item['value'], 'footprint': item['footprint'], 'refdes': [item['refdes']], 'part': item['part']}

    csv_data.append('"Comment","Designator","Footprint","LCPCB Part Number"')
    for key, item in grouped_bom.items():
        designators = ','.join(item['refdes'])
        csv_data.append(f'"{key[0]}","{designators}","{key[1]}","{item["part"]}"')

    return '\n'.join(csv_data)

def read_csv_content(csv_filename):
    with open(csv_filename, 'r') as file:
        return file.read()

def find_part_in_csv_content(csv_content, value):
    for line in csv_content.split('\n'):
        # STRIP QUOTES
        line = line.replace('"','')
        fields = line.split(',')
        if len(fields) >= 3 and fields[0].lower() == value.lower():
            return fields[2]
    return None

def update_bom_items_with_parts_csv(bom_items, csv_filename):
    csv_content = read_csv_content(csv_filename)
    for bom_item in bom_items:
        value = bom_item['value']
        part = find_part_in_csv_content(csv_content, value)
        if part:
            bom_item['part'] = part
    return bom_items

csv_filename = sys.argv[2]  # Replace with your CSV file path
kicad_pcb_list = parse_kicad_pcb_file(sys.argv[1])

kicad_pcb_list = strip_symbols(kicad_pcb_list)
bom_items = extract_bom_items_from_pcb_list(kicad_pcb_list)
updated_bom_items = update_bom_items_with_parts_csv(bom_items, csv_filename)
bom_csv = bom_items_to_csv(updated_bom_items)

with open('output.csv', 'w') as output_file:
    output_file.write(bom_csv)
