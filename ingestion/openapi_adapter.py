import logging
import json
from typing import List, Dict, Any
from prance import ResolvingParser
from ingestion.base_adapter import BaseAdapter, IngestedChunk
from rag.chunking import chunk_for_spec

logger = logging.getLogger("karate_ai")

class OpenAPIAdapter(BaseAdapter):
    def ingest(self, source_path: str) -> List[IngestedChunk]:
        logger.info(f"Parsing OpenAPI spec: {source_path}")
        
        try:
            # ResolvingParser automatically resolves $ref references
            parser = ResolvingParser(source_path, backend='openapi-spec-validator')
            spec = parser.specification
        except Exception as e:
            logger.error(f"Failed to parse OpenAPI spec: {e}")
            raise
            
        chunks = []
        paths = spec.get('paths', {})
        
        # Determine global auth
        security_schemes = spec.get('components', {}).get('securitySchemes', {})
        global_security = spec.get('security', [])
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    continue
                    
                endpoint_tag = f"{method.upper()} {path}"
                
                # Extract auth for this specific operation
                auth_reqs = []
                op_security = operation.get('security', global_security)
                if op_security:
                    for sec_req in op_security:
                        for scheme_name in sec_req.keys():
                            if scheme_name in security_schemes:
                                scheme = security_schemes[scheme_name]
                                auth_reqs.append(f"{scheme.get('type')} ({scheme.get('scheme', scheme.get('in', ''))})")
                
                # Extract request body schema
                request_body_schema = None
                if 'requestBody' in operation and 'content' in operation['requestBody']:
                    for content_type, content in operation['requestBody']['content'].items():
                        if 'schema' in content:
                            request_body_schema = content['schema']
                            break  # Just take the first one (usually application/json)
                            
                # Extract responses
                responses = {}
                for status_code, response in operation.get('responses', {}).items():
                    resp_data = {"description": response.get('description', '')}
                    if 'content' in response:
                        for content_type, content in response['content'].items():
                            if 'schema' in content:
                                resp_data['schema'] = content['schema']
                                break
                    responses[status_code] = resp_data
                    
                endpoint_data = {
                    "method": method,
                    "path": path,
                    "summary": operation.get('summary', ''),
                    "description": operation.get('description', ''),
                    "parameters": operation.get('parameters', []),
                    "request_body": request_body_schema,
                    "responses": responses,
                    "auth": auth_reqs
                }
                
                content = chunk_for_spec(endpoint_data)
                
                chunk = IngestedChunk(
                    content=content,
                    origin_type="spec",
                    source_file=source_path,
                    endpoint_tag=endpoint_tag,
                    chunk_type="endpoint_definition",
                    metadata={
                        "summary": operation.get('summary', ''),
                        "has_request_body": request_body_schema is not None
                    }
                )
                chunks.append(chunk)
                
        logger.info(f"Extracted {len(chunks)} endpoints from OpenAPI spec")
        return chunks
