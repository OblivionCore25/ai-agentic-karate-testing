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
