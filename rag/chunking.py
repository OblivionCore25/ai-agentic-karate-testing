from typing import Dict, Any

def chunk_for_spec(endpoint_data: Dict[str, Any]) -> str:
    """Formats OpenAPI endpoint data into a readable text block for embedding."""
    lines = []
    lines.append(f"Endpoint: {endpoint_data['method'].upper()} {endpoint_data['path']}")
    
    if endpoint_data.get('summary'):
        lines.append(f"Summary: {endpoint_data['summary']}")
        
    if endpoint_data.get('description'):
        lines.append(f"Description: {endpoint_data['description']}")
        
    if endpoint_data.get('parameters'):
        lines.append("Parameters:")
        for param in endpoint_data['parameters']:
            req = "required" if param.get('required') else "optional"
            lines.append(f"  - {param['name']} ({param['in']}): {param.get('description', '')} [{req}]")
            
    if endpoint_data.get('request_body'):
        lines.append("Request Body Schema:")
        lines.append(str(endpoint_data['request_body']))
        
    if endpoint_data.get('responses'):
        lines.append("Responses:")
        for status, resp in endpoint_data['responses'].items():
            lines.append(f"  - {status}: {resp.get('description', '')}")
            if resp.get('schema'):
                lines.append(f"    Schema: {str(resp['schema'])}")
                
    if endpoint_data.get('auth'):
        lines.append(f"Authentication: {', '.join(endpoint_data['auth'])}")
        
    return "\n".join(lines)

def chunk_for_code(class_info: Dict[str, Any], method_info: Dict[str, Any]) -> str:
    """Formats Java method with class context."""
    lines = []
    lines.append(f"[Class: {class_info['name']}]")
    if class_info.get('annotations'):
        lines.append(f"[Class Annotations: {', '.join(class_info['annotations'])}]")
        
    lines.append(f"[Method: {method_info['name']}]")
    if method_info.get('annotations'):
        lines.append(f"[Method Annotations: {', '.join(method_info['annotations'])}]")
        
    lines.append(f"Return Type: {method_info.get('return_type', 'void')}")
    
    if method_info.get('parameters'):
        lines.append(f"Parameters: {', '.join(method_info['parameters'])}")
        
    lines.append("\nCode:")
    lines.append(method_info['body'])
    
    return "\n".join(lines)

def chunk_for_test(scenario_data: Dict[str, Any]) -> str:
    """Formats Karate scenario with optional data-driven pattern info."""
    lines = []
    lines.append(f"Scenario: {scenario_data['name']}")
    if scenario_data.get('tags'):
        lines.append(f"Tags: {', '.join(scenario_data['tags'])}")

    # Include data-driven pattern info
    if scenario_data.get('is_outline'):
        if scenario_data.get('data_files'):
            lines.append(f"Data Pattern: External data files ({', '.join(scenario_data['data_files'])})")
        elif scenario_data.get('has_examples_table'):
            lines.append("Data Pattern: Inline Examples table")

    lines.append("Steps:")
    for step in scenario_data['steps']:
        lines.append(f"  {step}")

    return "\n".join(lines)

def chunk_for_schema(table_info: Dict[str, Any]) -> str:
    """Formats database table metadata into a readable text block for embedding."""
    lines = []
    lines.append(f"Table: {table_info['table_name']} (schema: {table_info.get('schema', 'public')})")

    if table_info.get('comment'):
        lines.append(f"Description: {table_info['comment']}")

    lines.append("")
    lines.append("Columns:")
    for col in table_info.get('columns', []):
        annotations = []

        if col.get('is_primary_key'):
            annotations.append("PK")
        if not col.get('nullable', True):
            annotations.append("NOT NULL")
        if col.get('is_unique'):
            annotations.append("UNIQUE")
        if col.get('default'):
            annotations.append(f"DEFAULT {col['default']}")
        if col.get('is_foreign_key') and col.get('foreign_key_ref'):
            ref = col['foreign_key_ref']
            annotations.append(f"FK → {ref['referred_table']}.{ref['referred_column']}")

        ann_str = f" [{', '.join(annotations)}]" if annotations else ""
        comment_str = f"  -- {col['comment']}" if col.get('comment') else ""
        lines.append(f"  - {col['name']}: {col['type']}{ann_str}{comment_str}")

    # Check constraints
    checks = table_info.get('check_constraints', [])
    if checks:
        lines.append("")
        lines.append("Check Constraints:")
        for cc in checks:
            name = cc.get('name', 'unnamed')
            expr = cc.get('sqltext', cc.get('expression', ''))
            lines.append(f"  - {name}: {expr}")

    # Indexes
    indexes = table_info.get('indexes', [])
    if indexes:
        lines.append("")
        lines.append("Indexes:")
        for idx in indexes:
            cols = ', '.join(idx.get('column_names', []))
            unique_str = " [UNIQUE]" if idx.get('unique') else ""
            lines.append(f"  - {idx.get('name', 'unnamed')} ON ({cols}){unique_str}")

    # Foreign key relationships (summary)
    fks = table_info.get('foreign_keys', [])
    if fks:
        lines.append("")
        lines.append("Foreign Keys:")
        for fk in fks:
            src_cols = ', '.join(fk.get('constrained_columns', []))
            ref_table = fk.get('referred_table', '')
            ref_cols = ', '.join(fk.get('referred_columns', []))
            options = fk.get('options', {})
            on_delete = f" ON DELETE {options['ondelete']}" if options.get('ondelete') else ""
            on_update = f" ON UPDATE {options['onupdate']}" if options.get('onupdate') else ""
            lines.append(f"  - {src_cols} → {ref_table}.{ref_cols}{on_delete}{on_update}")

    return "\n".join(lines)

