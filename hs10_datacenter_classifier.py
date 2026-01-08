"""
HS10 Data Center Relevance Classifier

This script classifies HS10 commodity codes by their relevance to data center construction,
based on a materials list of ~185 items across 20 categories.

Usage in Jupyter Notebook:
--------------------------
1. Place this file in the same directory as your data files, or add its location to your path
2. In a Jupyter cell, run:

    # Option A: Run as a script
    %run hs10_datacenter_classifier.py
    
    # Option B: Import and use functions
    from hs10_datacenter_classifier import classify_hs10_file, classify_single_code
    
    # Classify a full file
    results_df = classify_hs10_file('unique_hs10_commodities.csv', 'output_classification.csv')
    
    # Or classify a single code
    relevance, mapping = classify_single_code("AUTOMATIC DATA PROCESSING MACHINES")

Input File Requirements:
------------------------
CSV file with columns:
- I_COMMODITY: The HS10 code (10-digit)
- I_COMMODITY_LDESC: Description of the commodity

Output:
-------
CSV file with columns:
- HS10_Code: Original code
- Description: Original description  
- Relevance: High, Medium, or Low
- Materials_List_Mapping: Which data center material category it maps to

Author: Generated for trade policy research
Date: January 2025
"""

import pandas as pd
import re
from typing import Tuple, Optional

# =============================================================================
# CLASSIFICATION RULES
# =============================================================================

# Rules are checked in order - more specific matches should come first
# Format: (keyword, relevance, material_item, category)

CLASSIFICATION_RULES = [
    # ===== SPECIFIC EXCLUSIONS (check first to avoid false positives) =====
    ('cooling medium pumps for internal combustion', 'Low', 'Engine cooling pumps (not DC)', 'Not DC related'),
    ('marine propulsion', 'Low', 'Marine engines (not DC)', 'Not DC related'),
    ('motor vehicle', 'Low', 'Vehicle parts (not DC)', 'Not DC related'),
    ('woodworking', 'Low', 'Woodworking machines (not DC)', 'Not DC related'),
    ('textile fiber', 'Low', 'Textile machines (not DC)', 'Not DC related'),
    ('textile machine', 'Low', 'Textile machines (not DC)', 'Not DC related'),
    ('turbocharger', 'Low', 'Engine parts (not DC)', 'Not DC related'),
    ('supercharger', 'Low', 'Engine parts (not DC)', 'Not DC related'),
    
    # ===== HIGH RELEVANCE - SPECIFIC MATCHES =====
    
    # Data Center IT Equipment
    ('cooling microprocessors', 'High', 'Fans for IT equipment', 'Cooling Systems'),
    ('water chillers', 'High', 'Chillers', 'Cooling Systems'),
    ('heat exchange units', 'High', 'Heat exchangers', 'Cooling Systems'),
    ('heat exchangers', 'High', 'Heat exchangers', 'Cooling Systems'),
    ('switching and routing', 'High', 'Network switches/routers', 'Networking'),
    ('data processing machine', 'High', 'Servers/ADP machines', 'Compute Components'),
    ('automatic data processing', 'High', 'ADP/Servers', 'Compute Components'),
    ('adp machine', 'High', 'ADP/Servers', 'Compute Components'),
    ('disk drive', 'High', 'Storage drives', 'Storage Systems'),
    
    # Electrical Systems
    ('automatic circuit breaker', 'High', 'Circuit breakers', 'Electrical Systems'),
    ('isolating switch', 'High', 'Electrical switches', 'Electrical Systems'),
    ('make-and-break switch', 'High', 'Electrical switches', 'Electrical Systems'),
    ('electrical switching', 'High', 'Electrical switching apparatus', 'Electrical Systems'),
    ('inverters (static converters)', 'High', 'Inverters', 'Power Infrastructure'),
    ('static converter', 'High', 'Static converters', 'Electrical Systems'),
    ('rectifiers and rectifying', 'High', 'Rectifiers', 'Electrical Systems'),
    ('power supplies', 'High', 'Power supplies', 'Electrical Systems'),
    
    # Power & Batteries
    ('storage battery', 'High', 'Battery systems', 'Power Infrastructure'),
    ('electric accumulator', 'High', 'Battery systems', 'Power Infrastructure'),
    ('electric storage', 'High', 'Battery systems', 'Power Infrastructure'),
    ('lithium-ion accumulator', 'High', 'Li-ion battery systems', 'Power Infrastructure'),
    ('lithium ion accumulator', 'High', 'Li-ion battery systems', 'Power Infrastructure'),
    ('primary battery', 'Medium', 'Batteries', 'Power Infrastructure'),
    ('primary cell', 'Medium', 'Batteries', 'Power Infrastructure'),
    
    # Cooling & HVAC
    ('fan coil unit', 'High', 'Fan coil units', 'Cooling Systems'),
    ('central station air handler', 'High', 'Air handling units', 'Cooling Systems'),
    ('year-round unit', 'High', 'HVAC units', 'Cooling Systems'),
    ('fans of a kind used solely', 'High', 'IT cooling fans', 'Cooling Systems'),
    ('centrifugal pump', 'High', 'Cooling pumps', 'Cooling Systems'),
    
    # Networking
    ('optical fiber', 'High', 'Fiber optic cables', 'Networking'),
    ('optical fibers', 'High', 'Fiber optic cables', 'Networking'),
    ('transmission or reception', 'High', 'Telecommunications equipment', 'Networking'),
    ('wired or wireless network', 'High', 'Network equipment', 'Networking'),
    ('communication in a wired', 'High', 'Network equipment', 'Networking'),
    ('cellular network', 'Medium', 'Network equipment', 'Networking'),
    ('wireless network', 'Medium', 'Network equipment', 'Networking'),
    
    # Generators
    ('dc generator', 'High', 'Generators', 'Power Infrastructure'),
    ('ac generator', 'High', 'Generators', 'Power Infrastructure'),
    ('generating set', 'High', 'Generator sets', 'Power Infrastructure'),
    ('gas turbine', 'High', 'Gas turbines', 'Power Infrastructure'),
    ('steam turbine', 'Medium', 'Steam turbines', 'Power Infrastructure'),
    
    # ===== HIGH RELEVANCE - GENERAL MATCHES =====
    
    # Compute & Semiconductors
    ('graphics processing', 'High', 'AI accelerator dies (GPU)', 'Compute Components'),
    ('gpu', 'High', 'AI accelerator dies (GPU)', 'Compute Components'),
    ('integrated circuit', 'High', 'CPU dies / AI accelerators', 'Compute Components'),
    ('semiconductor', 'High', 'CPU dies / AI accelerators', 'Compute Components'),
    ('microprocessor', 'High', 'CPU dies', 'Compute Components'),
    ('processor', 'High', 'CPU dies', 'Compute Components'),
    ('printed circuit', 'High', 'PCBs (FR-4, high-layer)', 'Compute Components'),
    ('circuit board', 'High', 'PCBs (FR-4, high-layer)', 'Compute Components'),
    ('pcb', 'High', 'PCBs (FR-4, high-layer)', 'Compute Components'),
    ('memory module', 'High', 'DRAM DIMMs', 'Compute Components'),
    ('dram', 'High', 'DRAM DIMMs', 'Compute Components'),
    ('flash memory', 'High', 'NAND flash packages', 'Storage Systems'),
    ('solid-state', 'High', 'NAND flash packages', 'Storage Systems'),
    ('solid state storage', 'High', 'NAND flash packages', 'Storage Systems'),
    ('solid state drive', 'High', 'NAND flash packages', 'Storage Systems'),
    ('ssd', 'High', 'NAND flash packages', 'Storage Systems'),
    ('hard disk', 'High', 'HDD assemblies', 'Storage Systems'),
    ('magnetic disk storage', 'High', 'HDD assemblies', 'Storage Systems'),
    ('data storage', 'High', 'Storage systems', 'Storage Systems'),
    ('server', 'High', 'Server chassis', 'Compute Components'),
    
    # Electrical Power Systems
    ('transformer', 'High', 'Medium-voltage transformers', 'Electrical Systems'),
    ('switchgear', 'High', 'Medium-voltage switchgear', 'Electrical Systems'),
    ('electric cable', 'High', 'Power cables', 'Electrical Systems'),
    ('power cable', 'High', 'Power cables', 'Electrical Systems'),
    ('insulated wire', 'High', 'Power cables', 'Electrical Systems'),
    ('insulated cable', 'High', 'Power cables', 'Electrical Systems'),
    ('copper wire', 'High', 'Power cables', 'Electrical Systems'),
    ('copper conductor', 'High', 'Power cables / Busbars', 'Electrical Systems'),
    ('busbar', 'High', 'Busbars', 'Electrical Systems'),
    ('bus bar', 'High', 'Busbars', 'Electrical Systems'),
    ('circuit breaker', 'High', 'Circuit breakers', 'Electrical Systems'),
    ('generator', 'High', 'Diesel generators', 'Power Infrastructure'),
    ('diesel engine', 'High', 'Diesel generators', 'Power Infrastructure'),
    ('compression-ignition', 'High', 'Diesel generators', 'Power Infrastructure'),
    ('uninterruptible power', 'High', 'UPS systems', 'Power Infrastructure'),
    ('ups ', 'High', 'UPS systems', 'Power Infrastructure'),
    ('lithium-ion', 'High', 'Battery systems (Li-ion)', 'Power Infrastructure'),
    ('lithium ion', 'High', 'Battery systems (Li-ion)', 'Power Infrastructure'),
    ('accumulator', 'High', 'Battery systems', 'Power Infrastructure'),
    ('lead-acid', 'High', 'Battery systems', 'Power Infrastructure'),
    ('power supply unit', 'High', 'Power supply units (PSUs)', 'Compute Components'),
    ('rectifier', 'High', 'Rectifiers', 'Electrical Systems'),
    ('inverter', 'High', 'Inverters', 'Electrical Systems'),
    ('capacitor', 'High', 'Capacitors', 'Electrical Systems'),
    ('electrical panel', 'High', 'Distribution panels', 'Electrical Systems'),
    ('distribution board', 'High', 'Distribution panels', 'Electrical Systems'),
    ('switchboard', 'High', 'Switchboards', 'Electrical Systems'),
    ('electrical conduit', 'High', 'Conduit systems', 'Electrical Systems'),
    
    # Cooling Systems
    ('air conditioning', 'High', 'CRAC/CRAH units', 'Cooling Systems'),
    ('air-conditioning', 'High', 'CRAC/CRAH units', 'Cooling Systems'),
    ('chiller', 'High', 'Chillers', 'Cooling Systems'),
    ('cooling tower', 'High', 'Cooling towers', 'Cooling Systems'),
    ('heat exchanger', 'High', 'Heat exchangers / CDUs', 'Cooling Systems'),
    ('water pump', 'High', 'Water pumping stations', 'Cooling Systems'),
    ('axial fan', 'High', 'Axial fans', 'Cooling Systems'),
    ('centrifugal fan', 'High', 'Centrifugal fans', 'Cooling Systems'),
    ('ventilating fan', 'High', 'Ventilation fans', 'Cooling Systems'),
    ('refrigerant', 'High', 'DLC coolant fluids', 'Cooling Systems'),
    ('refrigerating', 'High', 'Cooling equipment', 'Cooling Systems'),
    ('coolant', 'High', 'DLC coolant fluids', 'Cooling Systems'),
    ('ethylene glycol', 'High', 'DLC coolant fluids', 'Cooling Systems'),
    ('propylene glycol', 'High', 'DLC coolant fluids', 'Cooling Systems'),
    ('heat sink', 'High', 'Copper heatsinks', 'Thermal Management'),
    ('heatsink', 'High', 'Copper heatsinks', 'Thermal Management'),
    ('thermal paste', 'High', 'Thermal interface materials', 'Thermal Management'),
    ('thermal compound', 'High', 'Thermal interface materials', 'Thermal Management'),
    ('air filter', 'High', 'Air filters', 'Cooling Systems'),
    ('hvac', 'High', 'HVAC systems', 'Cooling Systems'),
    ('damper', 'Medium', 'Ductwork & dampers', 'Cooling Systems'),
    ('thermostat', 'Medium', 'Temperature controls', 'Cooling Systems'),
    ('compressor', 'High', 'Compressors (cooling)', 'Cooling Systems'),
    ('centrifugal', 'Medium', 'Fans/pumps', 'Cooling Systems'),
    ('axial', 'Medium', 'Axial fans', 'Cooling Systems'),
    
    # Networking & Fiber
    ('fiber optic', 'High', 'Fiber optic cables', 'Networking'),
    ('fibre optic', 'High', 'Fiber optic cables', 'Networking'),
    ('optical cable', 'High', 'Fiber optic cables', 'Networking'),
    ('transceiver', 'High', 'Optical transceivers', 'Networking'),
    ('router', 'High', 'Routers', 'Networking'),
    ('network switch', 'High', 'Network switches', 'Networking'),
    ('switching apparatus', 'High', 'Network switches', 'Networking'),
    ('ethernet', 'High', 'Network switches', 'Networking'),
    ('lan equipment', 'High', 'Network equipment', 'Networking'),
    ('network interface', 'High', 'Network interface cards', 'Networking'),
    ('data transmission', 'High', 'Networking equipment', 'Networking'),
    ('telecommunication', 'High', 'Networking equipment', 'Networking'),
    ('coaxial cable', 'High', 'Cables', 'Networking'),
    ('electrical connector', 'Medium', 'Cable connectors', 'Networking'),
    
    # Building Structure
    ('structural steel', 'High', 'Structural steel', 'Building Structure'),
    ('steel beam', 'High', 'Structural steel', 'Building Structure'),
    ('steel column', 'High', 'Structural steel', 'Building Structure'),
    ('h-beam', 'High', 'Structural steel', 'Building Structure'),
    ('i-beam', 'High', 'Structural steel', 'Building Structure'),
    ('wide flange', 'High', 'Structural steel', 'Building Structure'),
    ('reinforcing bar', 'High', 'Rebar', 'Building Structure'),
    ('rebar', 'High', 'Rebar', 'Building Structure'),
    ('iron bar', 'Medium', 'Rebar', 'Building Structure'),
    ('steel bar', 'High', 'Rebar', 'Building Structure'),
    ('portland cement', 'High', 'Concrete', 'Building Structure'),
    ('hydraulic cement', 'High', 'Concrete', 'Building Structure'),
    ('ready-mix', 'High', 'Concrete', 'Building Structure'),
    ('concrete', 'High', 'Concrete', 'Building Structure'),
    ('seismic', 'High', 'Seismic bracing', 'Building Structure'),
    
    # Building Envelope
    ('insulation material', 'High', 'Insulated wall panels', 'Building Envelope'),
    ('mineral wool', 'High', 'Insulation', 'Building Envelope'),
    ('glass fiber insulation', 'High', 'Insulation', 'Building Envelope'),
    ('roofing membrane', 'High', 'Roofing membranes', 'Building Envelope'),
    ('roofing material', 'High', 'Roofing materials', 'Building Envelope'),
    ('wall panel', 'High', 'Insulated wall panels', 'Building Envelope'),
    ('sandwich panel', 'High', 'Insulated wall panels', 'Building Envelope'),
    ('metal cladding', 'Medium', 'Wall cladding', 'Building Envelope'),
    ('steel door', 'Medium', 'Doors', 'Building Envelope'),
    ('fire door', 'High', 'Fire-rated doors', 'Building Envelope'),
    
    # Fire Suppression & Safety
    ('fire extinguishing', 'High', 'Fire suppression systems', 'Fire & Safety'),
    ('fire suppression', 'High', 'Fire suppression systems', 'Fire & Safety'),
    ('sprinkler', 'High', 'Fire suppression systems', 'Fire & Safety'),
    ('fire alarm', 'High', 'Fire detection systems', 'Fire & Safety'),
    ('smoke detector', 'High', 'Fire detection systems', 'Fire & Safety'),
    ('fire detection', 'High', 'Fire detection systems', 'Fire & Safety'),
    
    # Security
    ('cctv', 'High', 'Security cameras (CCTV)', 'Security'),
    ('surveillance camera', 'High', 'Security cameras', 'Security'),
    ('video camera', 'Medium', 'Security cameras', 'Security'),
    ('access control', 'High', 'Access control systems', 'Security'),
    ('biometric', 'High', 'Biometric access systems', 'Security'),
    ('security fence', 'Medium', 'Perimeter fencing', 'Site Infrastructure'),
    ('chain link', 'Medium', 'Perimeter fencing', 'Site Infrastructure'),
    ('bollard', 'Medium', 'Security bollards', 'Security'),
    
    # Racks & Containment
    ('server rack', 'High', 'Server racks', 'IT Infrastructure'),
    ('equipment rack', 'High', 'Server racks', 'IT Infrastructure'),
    ('19-inch rack', 'High', 'Server racks', 'IT Infrastructure'),
    ('cabinet', 'Medium', 'Server racks/cabinets', 'IT Infrastructure'),
    ('raised floor', 'High', 'Raised floor systems', 'Building Structure'),
    ('access floor', 'High', 'Raised floor systems', 'Building Structure'),
    
    # Plumbing & Piping
    ('steel pipe', 'Medium', 'Piping systems', 'Site Infrastructure'),
    ('copper pipe', 'Medium', 'Piping systems', 'Site Infrastructure'),
    ('pvc pipe', 'Medium', 'Piping systems', 'Site Infrastructure'),
    ('pipe fitting', 'Medium', 'Pipe fittings', 'Site Infrastructure'),
    ('valve', 'Medium', 'Valves', 'Various'),
    ('water tank', 'High', 'Water storage tanks', 'Site Infrastructure'),
    ('storage tank', 'High', 'Storage tanks', 'Site Infrastructure'),
    ('fuel tank', 'High', 'Fuel storage tanks', 'Power Infrastructure'),
    
    # Specialty Materials
    ('refined copper', 'High', 'Copper alloys', 'Specialty Materials'),
    ('copper cathode', 'High', 'Copper alloys', 'Specialty Materials'),
    ('copper alloy', 'High', 'Copper alloys', 'Specialty Materials'),
    ('aluminum alloy', 'High', 'Aluminum alloys', 'Specialty Materials'),
    ('aluminium alloy', 'High', 'Aluminum alloys', 'Specialty Materials'),
    ('aluminum plate', 'High', 'Aluminum alloys', 'Specialty Materials'),
    ('aluminum sheet', 'High', 'Aluminum alloys', 'Specialty Materials'),
    ('rare-earth', 'High', 'Neodymium-iron-boron magnets', 'Specialty Materials'),
    ('rare earth', 'High', 'Neodymium-iron-boron magnets', 'Specialty Materials'),
    ('neodymium', 'High', 'Neodymium-iron-boron magnets', 'Specialty Materials'),
    ('permanent magnet', 'High', 'Neodymium-iron-boron magnets', 'Specialty Materials'),
    ('tantalum', 'High', 'Tantalum capacitors', 'Specialty Materials'),
    ('gallium', 'High', 'Gallium compounds', 'Specialty Materials'),
    ('indium', 'High', 'Indium compounds', 'Specialty Materials'),
    ('germanium', 'High', 'Germanium', 'Specialty Materials'),
    ('silicon wafer', 'High', 'Silicon substrates', 'Compute Components'),
    ('polysilicon', 'High', 'Silicon materials', 'Compute Components'),
    ('monocrystalline silicon', 'High', 'Silicon materials', 'Compute Components'),
    ('solder', 'High', 'Lead-free solder', 'Compute Components'),
    ('epoxy resin', 'Medium', 'Underfill & encapsulants', 'Compute Components'),
    ('silicone', 'Medium', 'Thermal materials/sealants', 'Various'),
    
    # Monitoring & Control
    ('temperature sensor', 'High', 'Environmental sensors', 'Monitoring & BMS'),
    ('humidity sensor', 'High', 'Environmental sensors', 'Monitoring & BMS'),
    ('pressure sensor', 'High', 'Environmental sensors', 'Monitoring & BMS'),
    ('flow meter', 'High', 'Metering equipment', 'Monitoring & BMS'),
    ('electric meter', 'High', 'Metering equipment', 'Monitoring & BMS'),
    ('programmable logic controller', 'High', 'PLC systems', 'Monitoring & BMS'),
    ('plc', 'High', 'PLC systems', 'Monitoring & BMS'),
    ('building management', 'High', 'BMS systems', 'Monitoring & BMS'),
    
    # Sustainability
    ('solar cell', 'High', 'Solar panels', 'Sustainability'),
    ('solar panel', 'High', 'Solar panels', 'Sustainability'),
    ('photovoltaic', 'High', 'Solar panels', 'Sustainability'),
    ('solar module', 'High', 'Solar panels', 'Sustainability'),
    
    # ===== MEDIUM RELEVANCE =====
    
    ('electric motor', 'Medium', 'Motors (fans, pumps)', 'Various'),
    ('ac motor', 'Medium', 'Motors', 'Various'),
    ('dc motor', 'Medium', 'Motors', 'Various'),
    ('electric', 'Medium', 'Various electrical', 'Electrical Systems'),
    ('electronic', 'Medium', 'Electronic components', 'Compute Components'),
    ('diode', 'Medium', 'Electronic components', 'Compute Components'),
    ('transistor', 'Medium', 'Electronic components', 'Compute Components'),
    ('resistor', 'Medium', 'Electronic components', 'Compute Components'),
    ('inductor', 'Medium', 'Electronic components', 'Compute Components'),
    ('relay', 'Medium', 'Electrical relays', 'Electrical Systems'),
    ('fuse', 'Medium', 'Electrical fuses', 'Electrical Systems'),
    ('wire', 'Medium', 'Wiring', 'Electrical Systems'),
    ('cable', 'Medium', 'Cables', 'Various'),
    ('conduit', 'Medium', 'Conduit systems', 'Electrical Systems'),
    ('duct', 'Medium', 'Ductwork', 'Cooling Systems'),
    ('insulated', 'Medium', 'Insulated materials', 'Various'),
    ('plastic tube', 'Medium', 'Plastic tubing', 'Various'),
    ('rubber tube', 'Medium', 'Rubber tubing', 'Various'),
    ('gasket', 'Medium', 'Seals and gaskets', 'Various'),
    ('o-ring', 'Medium', 'Seals', 'Various'),
    ('bolt', 'Medium', 'Fasteners', 'Building Structure'),
    ('screw', 'Medium', 'Fasteners', 'Building Structure'),
    ('fastener', 'Medium', 'Fasteners', 'Building Structure'),
    ('welding', 'Medium', 'Welding materials', 'Building Structure'),
    ('weld', 'Medium', 'Welding materials', 'Building Structure'),
    ('adhesive', 'Medium', 'Adhesives', 'Various'),
    ('sealant', 'Medium', 'Sealants', 'Various'),
    ('diesel fuel', 'High', 'Diesel for generators', 'Power Infrastructure'),
    ('diesel oil', 'High', 'Diesel for generators', 'Power Infrastructure'),
    ('led', 'Medium', 'LED lighting', 'Electrical Systems'),
    ('lighting', 'Medium', 'Lighting systems', 'Electrical Systems'),
    ('luminaire', 'Medium', 'Lighting fixtures', 'Electrical Systems'),
    ('floor tile', 'Low', 'Floor tiles', 'Building Structure'),
    ('ceiling', 'Low', 'Ceiling systems', 'Building Envelope'),
    ('paint', 'Low', 'Coatings', 'Building Envelope'),
    ('coating', 'Low', 'Protective coatings', 'Various'),
    ('lubricant', 'Low', 'Maintenance supplies', 'Various'),
    
    # Metals (general)
    ('copper', 'Medium', 'Copper materials', 'Specialty Materials'),
    ('aluminum', 'Medium', 'Aluminum materials', 'Specialty Materials'),
    ('aluminium', 'Medium', 'Aluminum materials', 'Specialty Materials'),
    ('steel', 'Medium', 'Steel materials', 'Building Structure'),
    ('iron', 'Medium', 'Iron/steel materials', 'Building Structure'),
    ('zinc', 'Medium', 'Zinc (galvanizing)', 'Building Structure'),
    ('nickel', 'Medium', 'Nickel alloys', 'Specialty Materials'),
    ('tin', 'Medium', 'Tin (solder)', 'Compute Components'),
]

# Patterns to skip (food, textiles, etc.)
SKIP_PATTERNS = [
    r'^(horse|cattle|swine|sheep|chicken|turkey|duck|goose|poultry|primate|whale|camel|rabbit|fox|dog|bird|bee|insect|fish|crustacean|mollusk)',
    r'^(meat|beef|pork|lamb|poultry|fish|milk|cream|butter|cheese|egg|honey|vegetable|fruit|nut|cereal|flour|sugar|cocoa|chocolate|coffee|tea|spice)',
    r'^(wine|beer|spirits|tobacco|cigar|cigarette)',
    r'^(cotton|wool|silk|flax|hemp|jute|yarn|thread|fabric|textile|carpet|rug|clothing|apparel|footwear|hat|glove)',
    r'^(wood|lumber|plywood|furniture|paper|cardboard|book|newspaper|magazine)',
    r'^(ceramic|porcelain|glass.*ware|tableware|kitchenware)',
    r'^(jewelry|jewellery|precious stone|diamond|ruby|emerald|pearl|gold.*jewelry|silver.*jewelry)',
    r'^(toy|game|sport|musical instrument|artwork|antique|coin|stamp)',
    r'^(pharmaceutical|medicament|drug|vaccine|antibiotic|vitamin|cosmetic|perfume|soap|shampoo)',
    r'^(live |fresh |frozen |dried |salted |smoked |canned |preserved )',
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def word_match(keyword: str, text: str) -> bool:
    """Check if keyword exists as a word or phrase (not substring) in text."""
    pattern = r'\b' + re.escape(keyword) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def classify_single_code(description: str) -> Tuple[str, str]:
    """
    Classify a single HS10 description.
    
    Parameters
    ----------
    description : str
        The commodity description text
        
    Returns
    -------
    tuple
        (relevance, mapping) where relevance is 'High', 'Medium', or 'Low'
        and mapping is the data center materials category
    """
    desc_lower = description.lower()
    
    # Check skip patterns first
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, desc_lower):
            return ('Low', 'No direct match - outside data center scope')
    
    # Check classification rules in order
    for rule in CLASSIFICATION_RULES:
        keyword, relevance, item, category = rule
        if word_match(keyword, desc_lower):
            return (relevance, f"{item} ({category})")
    
    # Default to Low
    return ('Low', 'No direct match')


def classify_hs10_file(input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
    """
    Classify all HS10 codes in a CSV file.
    
    Parameters
    ----------
    input_file : str
        Path to input CSV with columns 'I_COMMODITY' and 'I_COMMODITY_LDESC'
    output_file : str, optional
        Path to save output CSV. If None, results are only returned.
        
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: HS10_Code, Description, Relevance, Materials_List_Mapping
    """
    # Load input file
    df = pd.read_csv(input_file)
    
    # Validate columns
    required_cols = ['I_COMMODITY', 'I_COMMODITY_LDESC']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Input file must have columns: {required_cols}")
    
    # Classify each row
    results = []
    for idx, row in df.iterrows():
        hs10_code = row['I_COMMODITY']
        description = str(row['I_COMMODITY_LDESC'])
        relevance, mapping = classify_single_code(description)
        results.append({
            'HS10_Code': hs10_code,
            'Description': description,
            'Relevance': relevance,
            'Materials_List_Mapping': mapping
        })
    
    # Create output DataFrame
    output_df = pd.DataFrame(results)
    
    # Save if output path provided
    if output_file:
        output_df.to_csv(output_file, index=False)
        print(f"Results saved to: {output_file}")
    
    return output_df


def print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics for classified DataFrame."""
    print("=" * 70)
    print("CLASSIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total HS10 codes classified: {len(df):,}")
    print()
    print("Distribution by Relevance:")
    print(df['Relevance'].value_counts().to_string())
    print()
    
    # High relevance breakdown
    high_df = df[df['Relevance'] == 'High']
    print(f"\nHIGH Relevance Codes ({len(high_df)} total) - Top Categories:")
    print(high_df['Materials_List_Mapping'].value_counts().head(15).to_string())
    
    # Medium relevance breakdown
    med_df = df[df['Relevance'] == 'Medium']
    print(f"\nMEDIUM Relevance Codes ({len(med_df)} total) - Top Categories:")
    print(med_df['Materials_List_Mapping'].value_counts().head(10).to_string())


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Default file paths (modify as needed)
    DEFAULT_INPUT = "unique_hs10_commodities.csv"
    DEFAULT_OUTPUT = "hs10_datacenter_classification.csv"
    
    # Get file paths from command line or use defaults
    input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_file = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    
    print(f"Processing: {input_file}")
    print(f"Output to: {output_file}")
    print()
    
    # Run classification
    results = classify_hs10_file(input_file, output_file)
    
    # Print summary
    print_summary(results)
