"""
HS10 Data Center Classification using Claude Tool Calling (Option 2)

This script demonstrates using Claude's tool calling feature to get
structured, validated responses for classifying HS10 codes.

Usage:
    python hs10_llm_classifier_demo.py

Requirements:
    pip install anthropic pandas

You'll need an ANTHROPIC_API_KEY environment variable set.
"""

import anthropic
import pandas as pd
import json
import time
from typing import Optional

# Initialize the client
client = anthropic.Anthropic()

# =============================================================================
# DEFINE THE CLASSIFICATION TOOL
# =============================================================================

CLASSIFICATION_TOOL = {
    "name": "classify_hs10_code",
    "description": "Record the classification of an HS10 commodity code for its relevance to AI data center construction and operation",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevance": {
                "type": "string",
                "enum": ["High", "Medium", "Low"],
                "description": "How relevant is this product to AI data center construction or operation. High = directly used in data centers, Medium = sometimes used or indirect input, Low = not relevant"
            },
            "confidence": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Confidence in this assessment from 0 to 100"
            },
            "primary_category": {
                "type": "string",
                "enum": [
                    "Compute_Hardware",
                    "Networking_Telecom",
                    "Cooling_HVAC", 
                    "Electrical_Power",
                    "Building_Structure",
                    "Fire_Safety_Security",
                    "Specialty_Materials",
                    "Maintenance_Operations",
                    "Not_DC_Related"
                ],
                "description": "Primary use category for this product"
            },
            "specific_use": {
                "type": "string",
                "description": "Specific application in a data center context (e.g., 'GPU accelerators', 'backup generator fuel', 'server rack cooling')"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why this classification was chosen"
            }
        },
        "required": ["relevance", "confidence", "primary_category", "specific_use", "reasoning"]
    }
}

SYSTEM_PROMPT = """You are an expert in AI data center construction, operations, and supply chains. 

Your task is to classify HS10 commodity codes by their relevance to building and operating 
AI-focused data centers (hyperscale facilities running GPU clusters for training and inference).

Consider these categories of relevant products:
- COMPUTE: GPUs, CPUs, memory, PCBs, servers, storage drives, semiconductors
- NETWORKING: Fiber optics, switches, routers, transceivers, cables
- COOLING: Chillers, cooling towers, CRAH units, fans, pumps, refrigerants, glycol
- ELECTRICAL: Transformers, switchgear, UPS, batteries, generators, cables, busbars
- BUILDING: Structural steel, concrete, rebar, insulation, raised floors, fire suppression
- SPECIALTY MATERIALS: Rare earths, copper, aluminum, tantalum, thermal interface materials

Be thoughtful about edge cases:
- "Diesel engines" could be for generators (relevant) or vehicles (not relevant)
- "Pumps" could be for cooling systems (relevant) or unrelated industrial use
- "Copper wire" is relevant for electrical systems
- Food, textiles, furniture, and consumer goods are generally NOT relevant

Use the classify_hs10_code tool to record your assessment."""


def classify_single_code(hs10_code: str, description: str) -> dict:
    """
    Classify a single HS10 code using Claude with tool calling.
    
    Parameters
    ----------
    hs10_code : str
        The 10-digit HS code
    description : str
        The commodity description
        
    Returns
    -------
    dict
        Classification result with relevance, confidence, category, etc.
    """
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        tools=[CLASSIFICATION_TOOL],
        tool_choice={"type": "tool", "name": "classify_hs10_code"},
        messages=[{
            "role": "user", 
            "content": f"Classify this HS10 code:\n\nCode: {hs10_code}\nDescription: {description}"
        }]
    )
    
    # Extract the tool call result
    # When tool_choice forces a specific tool, content[0] will be a ToolUseBlock
    tool_use_block = response.content[0]
    
    # The 'input' field contains our structured data
    result = tool_use_block.input
    
    # Add metadata
    result['hs10_code'] = hs10_code
    result['description'] = description
    
    return result


def classify_batch(codes_and_descriptions: list, 
                   delay: float = 0.5,
                   checkpoint_file: Optional[str] = None) -> pd.DataFrame:
    """
    Classify multiple HS10 codes with rate limiting.
    
    Parameters
    ----------
    codes_and_descriptions : list
        List of tuples: [(code, description), ...]
    delay : float
        Seconds to wait between API calls
    checkpoint_file : str, optional
        Save progress to this file periodically
        
    Returns
    -------
    pd.DataFrame
        Classification results
    """
    results = []
    total = len(codes_and_descriptions)
    
    for i, (code, desc) in enumerate(codes_and_descriptions):
        try:
            result = classify_single_code(code, desc)
            results.append(result)
            
            print(f"[{i+1}/{total}] {code}: {result['relevance']} "
                  f"({result['confidence']}%) - {result['primary_category']}")
            
            # Checkpoint every 10 items
            if checkpoint_file and len(results) % 10 == 0:
                pd.DataFrame(results).to_csv(checkpoint_file, index=False)
            
            # Rate limiting
            time.sleep(delay)
            
        except Exception as e:
            print(f"[{i+1}/{total}] ERROR on {code}: {e}")
            results.append({
                'hs10_code': code,
                'description': desc,
                'relevance': 'Error',
                'confidence': 0,
                'primary_category': 'Error',
                'specific_use': '',
                'reasoning': str(e)
            })
    
    return pd.DataFrame(results)


def resume_batch_classification(
    all_codes_file: str,
    checkpoint_file: str,
    code_column: str = 'hs10_code',
    description_column: str = 'description',
    output_file: Optional[str] = None,
    delay: float = 0.5
) -> pd.DataFrame:
    """
    Resume batch classification by skipping already-processed codes.
    Handles crashes gracefully by reading from checkpoint file.
    
    Parameters
    ----------
    all_codes_file : str
        CSV file with all HS10 codes to classify
    checkpoint_file : str
        CSV file with partially completed results (will be created if doesn't exist)
    code_column : str
        Column name for HS10 codes (default: 'hs10_code')
    description_column : str
        Column name for descriptions (default: 'description')
    output_file : str, optional
        Final output file (default: same as checkpoint_file)
    delay : float
        Seconds between API calls (default: 0.5)
    
    Returns
    -------
    pd.DataFrame
        Combined results (old + new)
        
    Example
    -------
    >>> results = resume_batch_classification(
    ...     all_codes_file='unique_hs10_commodities.csv',
    ...     checkpoint_file='hs10_classification_progress.csv',
    ...     output_file='hs10_classification_final.csv'
    ... )
    """
    import os
    
    if output_file is None:
        output_file = checkpoint_file
    
    # Load all codes
    print(f"Loading all codes from: {all_codes_file}")
    all_codes_df = pd.read_csv(all_codes_file)
    print(f"Total codes to classify: {len(all_codes_df):,}")
    
    # Check if checkpoint exists
    if os.path.exists(checkpoint_file):
        print(f"\nFound checkpoint file: {checkpoint_file}")
        completed_df = pd.read_csv(checkpoint_file)
        print(f"Total rows in checkpoint: {len(completed_df):,} codes")
        
        # Filter out error rows - these should be retried
        error_rows = completed_df[completed_df['relevance'] == 'Error']
        success_rows = completed_df[completed_df['relevance'] != 'Error']
        
        if len(error_rows) > 0:
            print(f"Found {len(error_rows):,} error rows (will be retried)")
        print(f"Successfully completed: {len(success_rows):,} codes")
        
        # Only skip successfully completed codes
        completed_codes = set(success_rows['hs10_code'].astype(str))
        remaining_df = all_codes_df[~all_codes_df[code_column].astype(str).isin(completed_codes)]
        print(f"Remaining to classify: {len(remaining_df):,} codes")
        
        # Keep only successful results for final output
        completed_df = success_rows
    else:
        print(f"\nNo checkpoint file found. Starting fresh.")
        remaining_df = all_codes_df
        completed_df = pd.DataFrame()
    
    # If nothing left to do
    if len(remaining_df) == 0:
        print("\n✅ All codes already classified!")
        return completed_df
    
    # Prepare remaining codes
    codes_and_descriptions = list(zip(
        remaining_df[code_column].astype(str),
        remaining_df[description_column].astype(str)
    ))
    
    print(f"\n🚀 Starting classification of {len(codes_and_descriptions):,} remaining codes...")
    print(f"Progress will be saved to: {checkpoint_file}")
    
    # Classify remaining codes
    new_results_df = classify_batch(
        codes_and_descriptions,
        delay=delay,
        checkpoint_file=checkpoint_file
    )
    
    # Combine with previous results
    if len(completed_df) > 0:
        final_df = pd.concat([completed_df, new_results_df], ignore_index=True)
    else:
        final_df = new_results_df
    
    # Save final results
    final_df.to_csv(output_file, index=False)
    print(f"\n✅ Complete! Final results saved to: {output_file}")
    print(f"Total classified: {len(final_df):,} codes")
    
    return final_df


# =============================================================================
# DEMO: TEST WITH SAMPLE CODES
# =============================================================================

if __name__ == "__main__":
    
    # Sample HS10 codes to test - mix of relevant and irrelevant
    test_cases = [
        # Clearly relevant
        ("8542310040", "PROCESSORS (INCLUDING MICROPROCESSORS): GRAPHICS PROCESSING UNITS (GPUS)"),
        ("8471500000", "PROCESSING UNITS FOR AUTOMATIC DATA PROCESSING MACHINES"),
        ("8544700000", "INSULATED OPTICAL FIBER CABLES WITH INDIVIDUALLY SHEATHED FIBERS"),
        ("8507600020", "LITHIUM-ION STORAGE BATTERIES, NESOI"),
        ("8415820120", "AIR-CONDITIONERS, YEAR-ROUND UNITS (HEATING AND COOLING) EXCEEDING 17.58 KW/HR"),
        ("8504220080", "LIQUID DIELECTRIC TRANSFORMER HAVING A POWER HANDLING CAPACITY EXCEEDING 2,500 KVA"),
        
        # Ambiguous - could go either way
        ("8408909030", "COMPRESSION-IGNITION INTERNAL COMBUSTION PISTON ENGINES, NESOI, EXCEEDING 373 KW"),
        ("8413702015", "CENTRIFUGAL PUMPS FOR LIQUIDS, SINGLE-STAGE, DISCHARGE OUTLET 5.08 CM OR OVER"),
        ("7408110000", "REFINED COPPER WIRE, OF WHICH THE MAXIMUM CROSS-SECTIONAL DIMENSION EXCEEDS 6 MM"),
        ("3824999297", "CHEMICAL PRODUCTS AND PREPARATIONS, NESOI"),
        
        # Clearly NOT relevant
        ("0201200200", "BEEF WITH BONE IN, HIGH-QUALITY CUTS, PROCESSED, FRESH OR CHILLED"),
        ("6110201075", "SWEATERS, PULLOVERS AND SIMILAR ARTICLES, KNITTED, OF COTTON"),
        ("9503000090", "TOYS, NESOI"),
        ("2204210060", "WINE, GRAPE, STILL, IN CONTAINERS HOLDING 2 LITERS OR LESS"),
    ]
    
    print("=" * 80)
    print("HS10 CLASSIFICATION DEMO USING CLAUDE TOOL CALLING")
    print("=" * 80)
    print()
    print(f"Testing {len(test_cases)} sample codes...")
    print()
    
    # Classify each test case
    results = []
    for code, desc in test_cases:
        print("-" * 60)
        print(f"Code: {code}")
        print(f"Desc: {desc[:70]}...")
        
        try:
            result = classify_single_code(code, desc)
            results.append(result)
            
            print(f"\n  RELEVANCE:  {result['relevance']}")
            print(f"  CONFIDENCE: {result['confidence']}%")
            print(f"  CATEGORY:   {result['primary_category']}")
            print(f"  USE:        {result['specific_use']}")
            print(f"  REASONING:  {result['reasoning']}")
            
        except Exception as e:
            print(f"\n  ERROR: {e}")
            
        print()
        time.sleep(0.5)  # Rate limiting
    
    # Create summary DataFrame
    df = pd.DataFrame(results)
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Results by Relevance:")
    print(df['relevance'].value_counts().to_string())
    print()
    print("Results by Category:")
    print(df['primary_category'].value_counts().to_string())
    
    # Save results
    output_file = "llm_classification_demo_results.csv"
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    # Show the raw structure of one result
    print()
    print("=" * 80)
    print("EXAMPLE RAW RESULT (showing the structured output)")
    print("=" * 80)
    print(json.dumps(results[0], indent=2))
